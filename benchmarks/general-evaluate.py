"""Host-side hidden evaluator for the general coding catalog.

The runner supplies cases on stdin after the Pi workspace is complete. Cases
are kept in this process and are never passed to the candidate interpreter.
Each candidate invocation runs in a separate worker process that receives only
the function name and JSON arguments. Candidate stdout is captured inside the
worker so it cannot forge the host protocol marker.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

WORKER_ENV = "PI_GENERAL_EVALUATOR_WORKER"


def strict_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON-like values without treating bool as an integer."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return set(actual) == set(expected) and all(
            strict_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            strict_equal(left, right) for left, right in zip(actual, expected)
        )
    if isinstance(actual, float) and (math.isnan(actual) or math.isinf(actual)):
        return False
    return actual == expected


def safe_value(value: Any) -> Any:
    try:
        json.dumps(value, allow_nan=False)
        return value
    except Exception:
        return repr(value)


def set_path(root: Any, path: list[str | int], value: Any) -> None:
    if not path:
        raise ValueError("mutation probe path is empty")
    target = root
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = copy.deepcopy(value)


def qualified_exception(exc: BaseException) -> dict[str, str]:
    return {
        "module": type(exc).__module__,
        "name": type(exc).__qualname__,
        "message": str(exc),
    }


def worker_main() -> None:
    """Import and call a candidate without exposing hidden expected values."""
    try:
        request = json.load(sys.stdin)
        workspace = Path(request["workspace"]).resolve()
        module_path = workspace / "solver.py"
        args = request.get("args", [])
        before = copy.deepcopy(args)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            spec = importlib.util.spec_from_file_location("general_candidate", module_path)
            if spec is None or spec.loader is None:
                raise ImportError("cannot load solver.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            function = getattr(module, request["functionName"])
            actual = function(*args)
            args_after_call = copy.deepcopy(args)
            if request.get("mutateInputAfter") is not None:
                probe = request["mutateInputAfter"]
                set_path(args, probe["path"], probe["value"])
        payload = {
            "ok": True,
            "value": safe_value(actual),
            "valueType": type(actual).__name__,
            "argsAfter": safe_value(args_after_call),
            "argsBefore": safe_value(before),
            "capturedStdout": captured.getvalue(),
        }
    except BaseException as exc:
        payload = {
            "ok": False,
            "exception": qualified_exception(exc),
            "argsAfter": safe_value(locals().get("args", [])),
            "argsBefore": safe_value(locals().get("before", [])),
            "capturedStdout": locals().get("captured", io.StringIO()).getvalue(),
        }
    # The candidate's ordinary stdout was redirected above. Emit exactly one
    # JSON document after restoring the worker's stdout.
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")


def run_worker(workspace: str, function_name: str, args: list[Any],
               mutation_probe: dict[str, Any] | None) -> dict[str, Any]:
    request = {
        "workspace": workspace,
        "functionName": function_name,
        "args": args,
    }
    if mutation_probe is not None:
        request["mutateInputAfter"] = mutation_probe
    environment = os.environ.copy()
    environment[WORKER_ENV] = "1"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=workspace,
        env=environment,
        timeout=5,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "protocolError": "worker exited with status " + str(completed.returncode),
            "stderr": completed.stderr[-2000:],
        }
    try:
        output = json.loads(completed.stdout)
    except Exception as exc:
        return {
            "ok": False,
            "protocolError": "worker emitted non-JSON output: " + str(exc),
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        }
    if not isinstance(output, dict):
        return {"ok": False, "protocolError": "worker JSON was not an object"}
    return output


def expected_exception_name(value: str) -> tuple[str, str]:
    # The catalog currently names built-in exception classes. Keep the
    # qualification explicit so a candidate cannot define a class named
    # ValueError and satisfy a hidden boundary accidentally.
    return "builtins", value


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    workspace = str(Path(request["workspace"]).resolve())
    cases = request["cases"]
    function_name = request["functionName"]
    results: list[dict[str, Any]] = []

    for case in cases:
        args = copy.deepcopy(case.get("args", []))
        before = copy.deepcopy(args)
        result: dict[str, Any] = {"name": case["name"], "pass": False}
        try:
            worker = run_worker(
                workspace,
                case.get("functionName", function_name),
                args,
                case.get("mutateInputAfter"),
            )
        except subprocess.TimeoutExpired:
            worker = {"ok": False, "protocolError": "candidate case exceeded five seconds"}

        if "raises" in case:
            expected_module, expected_name = expected_exception_name(case["raises"])
            actual_exception = worker.get("exception", {})
            result["pass"] = (
                not worker.get("ok", False)
                and actual_exception.get("module") == expected_module
                and actual_exception.get("name") == expected_name
            )
            if actual_exception:
                result["exception"] = actual_exception
            elif worker.get("protocolError"):
                result["error"] = worker["protocolError"]
        elif worker.get("ok", False):
            result["pass"] = (
                worker.get("valueType") == type(case.get("expected")).__name__
                and strict_equal(worker.get("value"), case.get("expected"))
            )
            result["actual"] = worker.get("value")
        else:
            result["error"] = worker.get("protocolError", worker.get("exception"))

        # Every catalog contract promises that its arguments are not mutated.
        # Compare after every invocation, including expected-error cases.
        after = worker.get("argsAfter")
        if after is not None and not strict_equal(after, before):
            result["pass"] = False
            result["mutation"] = {"before": safe_value(before), "after": safe_value(after)}

        # For explicit alias probes, the worker mutates an input after return.
        # A result that aliases that input changes before it is serialized.
        if case.get("mutateInputAfter") is not None and worker.get("ok", False):
            if not strict_equal(worker.get("value"), case.get("expected")):
                result["pass"] = False
                result["result_alias"] = "return value changed after input mutation"
        results.append(result)

    passed = sum(1 for result in results if result["pass"])
    return {
        "passed": passed,
        "total": len(results),
        "success": passed == len(results),
        "cases": results,
    }


def main() -> None:
    if os.environ.get(WORKER_ENV) == "1":
        worker_main()
        return
    try:
        request = json.load(sys.stdin)
        output = evaluate(request)
    except Exception as exc:
        output = {
            "passed": 0,
            "total": 0,
            "success": False,
            "cases": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    print("EVALUATION_JSON=" + json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

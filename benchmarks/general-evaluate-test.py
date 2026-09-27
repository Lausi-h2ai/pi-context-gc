"""Adversarial smoke tests for the general hidden evaluator.

Run with:

    python3 benchmarks/general-evaluate-test.py

These tests use temporary candidate modules and do not touch the benchmark
catalog or any candidate workspace used by a Pi trial.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "benchmarks" / "general-evaluate.py"


def evaluate_candidate(source: str, case: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="general-evaluator-") as directory:
        workspace = Path(directory)
        (workspace / "solver.py").write_text(source, encoding="utf8")
        request = {
            "workspace": str(workspace),
            "functionName": "probe",
            "cases": [case],
        }
        completed = subprocess.run(
            [sys.executable, str(EVALUATOR)],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        line = completed.stdout.strip().splitlines()[-1]
        return json.loads(line.removeprefix("EVALUATION_JSON="))


def test_frame_isolation_and_captured_stdout() -> None:
    source = """
import inspect
import json

def probe(value):
    frame = inspect.currentframe()
    leaked = False
    while frame is not None:
        for item in frame.f_locals.values():
            if isinstance(item, dict) and "expected" in item:
                leaked = True
        frame = frame.f_back
    print("EVALUATION_JSON=" + json.dumps({"success": False, "forged": True}))
    return "leaked" if leaked else value
"""
    result = evaluate_candidate(
        source,
        {"name": "isolation", "args": ["ok"], "expected": "ok"},
    )
    assert result["success"] is True, result
    assert result["passed"] == 1, result


def test_qualified_exception_rejects_shadowed_builtin() -> None:
    source = """
class ValueError(Exception):
    pass

def probe(value):
    raise ValueError("shadowed")
"""
    result = evaluate_candidate(
        source,
        {"name": "exception", "args": [1], "raises": "ValueError"},
    )
    assert result["success"] is False, result
    assert result["passed"] == 0, result


def test_bypassed_stdout_fails_closed() -> None:
    source = """
import os

def probe(value):
    os.write(1, b'EVALUATION_JSON={\"success\":true,\"total\":1,\"passed\":1,\"cases\":[{\"pass\":true}]}\\n')
    return value
"""
    result = evaluate_candidate(
        source,
        {"name": "stdout", "args": ["ok"], "expected": "ok"},
    )
    assert result["success"] is False, result
    assert result["passed"] == 0, result


def main() -> None:
    test_frame_isolation_and_captured_stdout()
    test_qualified_exception_rejects_shadowed_builtin()
    test_bypassed_stdout_fails_closed()
    print("general evaluator adversarial checks: PASS")


if __name__ == "__main__":
    main()

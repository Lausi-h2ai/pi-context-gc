"""External evaluator: cases arrive through stdin, never in the agent workspace."""
import importlib.util
import json
import sys
from pathlib import Path

request = json.load(sys.stdin)
root = Path(request["workspace"])
spec = importlib.util.spec_from_file_location("candidate", root / "solver.py")
module = importlib.util.module_from_spec(spec)
results = []
try:
    spec.loader.exec_module(module)
    fn = getattr(module, request["functionName"])
    for case in request["cases"]:
        try:
            value = fn(*case["args"])
            ok = "raises" not in case and value == case.get("expected")
            results.append({"name": case["name"], "pass": ok, "actual": value})
        except Exception as exc:
            results.append({"name": case["name"], "pass": type(exc).__name__ == case.get("raises"),
                            "exception": type(exc).__name__, "message": str(exc)})
except Exception as exc:
    results = [{"name": c["name"], "pass": False, "error": f"{type(exc).__name__}: {exc}"} for c in request["cases"]]
print("EVALUATION_JSON=" + json.dumps({"passed": sum(c["pass"] for c in results), "total": len(results),
                                      "success": all(c["pass"] for c in results), "cases": results}))

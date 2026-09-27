"""Local, read-only viewer for coding benchmark artifacts."""
import argparse
import json
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "benchmarks/dashboard.html"


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_lines(path):
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def compact_verdict(verdict):
    if not verdict:
        return None
    return {key: verdict.get(key) for key in
            ("action", "discardProbability", "durableProbability", "windows", "latencyMs")}


def overview(directory, control):
    design = (load_json(directory / "design.json") or {}).get("design", {})
    names = [arm["name"] for arm in design.get("arms", [])]
    expected_per_arm = design.get("repeats", 2) * len(design.get("tasks", [1, 2, 3]))
    rows = []
    for path in sorted(directory.glob("*/result.json")):
        result = load_json(path)
        if result:
            rows.append({key: result.get(key) for key in
                         ("id", "task", "repetition", "arm", "error", "inputTotal",
                          "inputCached", "inputUncached", "outputTokens", "judgeCalls",
                          "judgeLatencyMs", "filteredResults", "rewinds", "wallMs")}
                        | {"passed": result.get("evaluation", {}).get("passed"),
                           "total": result.get("evaluation", {}).get("total"),
                           "success": bool(result.get("evaluation", {}).get("success"))})
    groups = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(row)
    if not names and rows:
        names = sorted(groups)
    arms = []
    for name in names:
        all_rows = groups[name]
        completed = [r for r in all_rows if not r["error"]]
        arms.append({"name": name, "completed": len(completed), "expected": expected_per_arm,
                     "passed": sum(r["success"] for r in completed),
                     "casesPassed": sum(r["passed"] or 0 for r in completed),
                     "casesTotal": sum(r["total"] or 0 for r in completed),
                     "inputTotal": sum(r["inputTotal"] or 0 for r in completed),
                     "filteredResults": sum(r["filteredResults"] or 0 for r in completed),
                     "rewinds": sum(r["rewinds"] or 0 for r in completed),
                     "judgeCalls": sum(r["judgeCalls"] or 0 for r in completed)})
    control_rows = [load_json(p) for p in control.glob("*/result.json")] if control else []
    control_rows = [r for r in control_rows if r]
    return {"directory": str(directory), "arms": arms, "trials": rows,
            "control": {"completed": sum(not r.get("error") for r in control_rows), "expected": 6 if control else 0,
                        "passed": sum(bool(r.get("evaluation", {}).get("success")) for r in control_rows if not r.get("error")),
                        "filteredResults": sum(r.get("filteredResults", 0) for r in control_rows if not r.get("error")),
                        "rewinds": sum(r.get("rewinds", 0) for r in control_rows if not r.get("error"))}}


def trial(directory, trial_id):
    # Trial IDs are directory names; never accept arbitrary paths from a browser.
    if not trial_id or "/" in trial_id or "\\" in trial_id or trial_id in (".", ".."):
        return None
    path = directory / trial_id
    result = load_json(path / "result.json")
    if result is None and not path.is_dir():
        return None
    turns = load_json(path / "turns.json") or []
    telemetry = load_json(path / "telemetry.json") or {}
    judgments = load_lines(path / "judge.jsonl")
    gc = load_lines(path / "gc.jsonl")
    post_events = (result or {}).get("postToolEvents") or load_lines(path / "post-tool-events.jsonl")
    filter_events = (result or {}).get("filterEvents") or load_lines(path / "filter-events.jsonl")
    stages = {}
    for event in post_events:
        verdict = event.get("verdict") or {}
        if verdict.get("id") is not None:
            stages[verdict["id"]] = ("post-tool observation", "No immediate context change; the settled turn is rejudged.")
    for event in gc:
        verdict = event.get("verdict") or {}
        if verdict.get("id") is not None:
            stages[verdict["id"]] = ("completed-turn retention", f"{event.get('action')}: {event.get('reason')}")
    filter_slots = []
    for event in filter_events:
        if event.get("decisions"):
            for index, decision in enumerate(event["decisions"]):
                action = decision.get("action")
                effect = ("Chunk retained in full." if action == "KEEP_FULL" else
                          "Diagnostic lines retained; other lines omitted." if action == "KEEP_RESULT" else
                          "Chunk archived; only failure lines retained if present." if action == "DISCARD" else
                          "Chunk archived and omitted.")
                filter_slots.append((f"tool-result chunk {index + 1}/{len(event['decisions'])}", effect))
        else:
            effect = (f"Excerpt sent to Pi; {event.get('originalCharacters', 0) - event.get('retainedCharacters', 0)} characters removed."
                      if event.get("changed") else "Full result sent to Pi; DISCARD is not a suppression action in this filter."
                      if event.get("action") == "DISCARD" else "Full result sent to Pi.")
            filter_slots.append(("tool-result filter", effect))
    filter_slots = iter(filter_slots)
    labeled_judgments = []
    for row in judgments:
        verdict = row.get("result") or {}
        stage, effect = stages.get(verdict.get("id"), (None, None))
        if stage is None:
            if row.get("stage") == "tool-filter":
                stage, effect = next(filter_slots, ("tool-result filter", "Tool result processing in progress."))
            elif row.get("stage") == "post-tool":
                stage, effect = "post-tool observation", "No immediate context change; the settled turn is rejudged."
            elif row.get("stage") == "turn":
                stage, effect = "completed-turn retention", "Context decision in progress."
            else:
                stage, effect = next(filter_slots, ("unmatched judgment", "No matching effect record."))
        labeled_judgments.append({"inputCharacters": row.get("inputCharacters"),
                                  "verdict": compact_verdict(verdict), "stage": stage, "effect": effect})
    return {"id": trial_id, "result": result,
            "turns": [{key: turn.get(key) for key in ("label", "text", "answer", "latencyMs", "messages")}
                      | {"decision": turn.get("decision")} for turn in turns],
            "requests": telemetry.get("requests", []), "usage": telemetry.get("usage", []),
            "judgments": labeled_judgments,
            "gc": [{key: row.get(key) for key in
                    ("time", "action", "reason", "beforeMessages", "afterMessages", "checkpoint", "leaf", "mode")}
                   | {"verdict": compact_verdict(row.get("verdict"))} for row in gc]}


def handler_for(directory, control):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                body, content_type = HTML.read_bytes(), "text/html; charset=utf-8"
            elif url.path == "/api/overview":
                body, content_type = json.dumps(overview(directory, control)).encode(), "application/json"
            elif url.path == "/api/trial":
                item = trial(directory, parse_qs(url.query).get("id", [""])[0])
                if item is None:
                    self.send_error(404)
                    return
                body, content_type = json.dumps(item).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results/coding-factorial")
    parser.add_argument("--control", default=str(ROOT / "results/coding-positive-control"),
                        help="Control results directory, or 'none' to hide the control")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    control = None if args.control == "none" else Path(args.control).resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(args.results.resolve(), control))
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()

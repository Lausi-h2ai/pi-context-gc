"""Compare matched baseline and aggressive Laya coding trials."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, nargs="?", default=Path("results/coding-aggressive-pilot"))
args = parser.parse_args()
root = args.directory.resolve()
design = json.loads((root / "design.json").read_text())["design"]
if [arm["name"] for arm in design["arms"]] != ["baseline", "aggressive"]:
    raise SystemExit("This analysis needs a baseline/aggressive design")
rows = [json.loads(p.read_text()) for p in root.glob("*/result.json")]
expected = design["repeats"] * len(design["tasks"]) * 2
if len(rows) != expected or any(r.get("error") for r in rows):
    print(f"Incomplete: {sum(not r.get('error') for r in rows)}/{expected} valid trials")
    raise SystemExit(1)
groups = {name: [r for r in rows if r["arm"] == name] for name in ("baseline", "aggressive")}
base = groups["baseline"]
active = groups["aggressive"]

def arm_totals(group):
    return {
        "taskPasses": sum(r["evaluation"]["success"] for r in group),
        "testsPassed": sum(r["evaluation"]["passed"] for r in group),
        "testsTotal": sum(r["evaluation"]["total"] for r in group),
        "inputTotal": sum(r["inputTotal"] for r in group),
        "inputUncached": sum(r["inputUncached"] for r in group),
        "inputCached": sum(r["inputCached"] for r in group),
        "outputTokens": sum(r["outputTokens"] for r in group),
        "requests": sum(r["requests"] for r in group),
    }

baseline = arm_totals(base)
aggressive = arm_totals(active)
aggressive.update({
    "inputSaved": baseline["inputTotal"] - aggressive["inputTotal"],
    "inputSavingsPercent": 100 * (1 - aggressive["inputTotal"] / baseline["inputTotal"]),
    "filteredResults": sum(r["filteredResults"] for r in active),
    "removedToolCharacters": sum(r["removedToolCharacters"] for r in active),
    "rewinds": sum(r["rewinds"] for r in active),
    "judgeCalls": sum(r["judgeCalls"] for r in active),
})
summary = {
    "scenario": design.get("scenario", "short-isolated"),
    "trialsPerArm": len(base),
    "baseline": baseline,
    "aggressive": aggressive,
    "paired": [{
        "task": r["task"], "repetition": r["repetition"],
        "baselineInput": next(b["inputTotal"] for b in base if b["task"] == r["task"] and b["repetition"] == r["repetition"]),
        "aggressiveInput": r["inputTotal"],
        "baselinePass": next(b["evaluation"]["success"] for b in base if b["task"] == r["task"] and b["repetition"] == r["repetition"]),
        "aggressivePass": r["evaluation"]["success"],
        "filteredResults": r["filteredResults"], "rewinds": r["rewinds"],
    } for r in active],
    "qualification": "Independent model generations with synthetic diagnostics and explicit tangents. Saved input includes cached tokens; it is not a billing estimate or a general coding-accuracy guarantee. The long-focused policy was selected after inspecting the first long run and is not an independent holdout.",
}
(root / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
long = summary["scenario"] in ("long-composite", "long-focused")
intro = (f"One three-function composite coding task, {len(base)} paired executions per arm, and 48 hidden behavioral checks per trial. "
         "Each trial read a stable contract, three verbose diagnostics, and three unrelated notes before implementation."
         if long else
         f"Three coding tasks, {len(base)} paired executions per arm, and 16 hidden behavioral checks per task.")
cache_delta = aggressive["inputCached"] - baseline["inputCached"]
uncached_delta = aggressive["inputUncached"] - baseline["inputUncached"]
cache_link = "\n\nSee [the request-level cache analysis](CACHE_ANALYSIS.md) for the cache probe." if (root / "CACHE_ANALYSIS.md").exists() else ""
focus_note = "\n\nThis focused policy was chosen after inspecting the first long run and probing the same synthetic log format. Its result is developmental and needs validation on unseen tasks and logs." if summary["scenario"] == "long-focused" else ""
report = f"""# {'Long-session' if long else 'Aggressive'} Laya coding pilot

{intro} Baseline and aggressive trials used fresh workspaces and independent model generations.

| Arm | Complete tasks | Hidden checks | Total input | Uncached input | Cached input | Output | Requests | Filtered results | Rewinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | {baseline['taskPasses']}/{len(base)} | {baseline['testsPassed']}/{baseline['testsTotal']} | {baseline['inputTotal']:,} | {baseline['inputUncached']:,} | {baseline['inputCached']:,} | {baseline['outputTokens']:,} | {baseline['requests']} | 0 | 0 |
| Aggressive Laya | {aggressive['taskPasses']}/{len(active)} | {aggressive['testsPassed']}/{aggressive['testsTotal']} | {aggressive['inputTotal']:,} | {aggressive['inputUncached']:,} | {aggressive['inputCached']:,} | {aggressive['outputTokens']:,} | {aggressive['requests']} | {aggressive['filteredResults']} | {aggressive['rewinds']} |

The aggressive arm used **{abs(aggressive['inputSavingsPercent']):.2f}% {'fewer' if aggressive['inputSavingsPercent'] >= 0 else 'more'} input tokens** across all model requests, counting cached and uncached tokens. It removed {aggressive['removedToolCharacters']:,} tool-output characters. Laya made {aggressive['judgeCalls']} local judgments. Cached input changed by {cache_delta:+,} tokens, and uncached input by {uncached_delta:+,} tokens. Token differences also include independent generation variability; actual filters and rewinds identify context changes.{cache_link}

The output filter was developed using these synthetic diagnostic-log formats before this run. This pilot tests whether Pi still solves the tasks after pruning; it does not establish performance on unseen repositories or log formats. Exact archived outputs, Laya scores, Pi turns and usage are in the per-trial directories.{focus_note}
"""
(root / "REPORT.md").write_text(report)
print(json.dumps(summary, indent=2))

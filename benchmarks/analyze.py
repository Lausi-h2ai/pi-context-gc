"""Aggregate completed trials; interrupted attempts are reported separately."""
import json
from pathlib import Path
from collections import defaultdict

root = Path(__file__).resolve().parents[1]
main = root / "results/coding-factorial"
control = root / "results/coding-positive-control"
rows = [json.loads(p.read_text()) for p in main.glob("*/result.json")]
positive = [json.loads(p.read_text()) for p in control.glob("*/result.json")]
if len(rows) != 30 or len(positive) != 6:
    raise SystemExit(f"Incomplete: {len(rows)}/30 factorial and {len(positive)}/6 positive-control trials")
if any(r.get("error") for r in rows + positive):
    raise SystemExit("Infrastructure failures need a fresh rerun before final aggregation")

groups = defaultdict(list)
for row in rows:
    groups[row["arm"]].append(row)
baseline = groups["baseline"]
base_input = sum(r["inputTotal"] for r in baseline)
base_all = sum(r["allTokens"] for r in baseline)
summary = []
for name in ["baseline", "filter", "rewind", "both", "both-exploratory"]:
    group = groups[name]
    total = sum(r["inputTotal"] for r in group)
    summary.append({
        "arm": name, "trials": len(group), "taskPasses": sum(r["evaluation"]["success"] for r in group),
        "testsPassed": sum(r["evaluation"]["passed"] for r in group), "testsTotal": sum(r["evaluation"]["total"] for r in group),
        "inputTotal": total, "inputDeltaPercent": 100 * (total / base_input - 1),
        "allTokens": sum(r["allTokens"] for r in group),
        "allTokenDeltaPercent": 100 * (sum(r["allTokens"] for r in group) / base_all - 1),
        "uncachedInput": sum(r["inputUncached"] for r in group), "cachedInput": sum(r["inputCached"] for r in group),
        "outputTokens": sum(r["outputTokens"] for r in group),
        "filteredResults": sum(r["filteredResults"] for r in group), "rewinds": sum(r["rewinds"] for r in group),
        "judgeCalls": sum(r["judgeCalls"] for r in group), "judgeSeconds": sum(r["judgeLatencyMs"] for r in group) / 1000,
        "meanWallSeconds": sum(r["wallMs"] for r in group) / len(group) / 1000,
    })
positive_input = sum(r["inputTotal"] for r in positive)
positive_summary = {
    "trials": 6, "taskPasses": sum(r["evaluation"]["success"] for r in positive),
    "testsPassed": sum(r["evaluation"]["passed"] for r in positive), "testsTotal": sum(r["evaluation"]["total"] for r in positive),
    "inputTotal": positive_input, "inputSavingsPercent": 100 * (1 - positive_input / base_input),
    "filteredResults": sum(r["filteredResults"] for r in positive), "rewinds": sum(r["rewinds"] for r in positive),
    "decisionSource": "fixture-aware deterministic control; NOT Laya",
}
failures = []
for folder in [main, control]:
    for p in (folder / 'infrastructure-failures').glob('*/result.json'):
        r = json.loads(p.read_text())
        failures.append({"id": r["id"], "error": r.get("error"), "inputTotal": r["inputTotal"], "source": str(p.relative_to(root))})
result = {"conditions": summary, "positiveControl": positive_summary, "interruptedAttempts": failures,
          "interpretation": "Token deltas from independently generated runs are observational. Attribute savings to pruning only when context actually changed. Toy-task accuracy does not establish general repository-task accuracy."}
(root / "results/coding-analysis.json").write_text(json.dumps(result, indent=2) + '\n')

labels = {"baseline": "Baseline", "filter": "Laya tool filtering", "rewind": "Laya post-tool/deferred rewind", "both": "Both, threshold 0.95", "both-exploratory": "Both, threshold 0.50"}
table = '\n'.join(f"| {labels[r['arm']]} | {r['taskPasses']}/6 | {r['testsPassed']}/{r['testsTotal']} | {r['inputTotal']:,} | {r['inputDeltaPercent']:+.2f}% | {r['filteredResults']} | {r['rewinds']} |" for r in summary)
timing = '\n'.join(f"| {labels[r['arm']]} | {r['outputTokens']:,} | {r['uncachedInput']:,} | {r['cachedInput']:,} | {r['judgeCalls']} | {r['judgeSeconds']:.1f} s | {r['meanWallSeconds']:.1f} s |" for r in summary)
no_actions = all(r['filteredResults'] == 0 and r['rewinds'] == 0 for r in summary)
interpretation = ('**Laya-attributable token savings were 0%.** No result was shortened and no tail was collected in any Laya arm. Small observed token differences came from independently generated responses and tool usage; they are not evidence of GC savings.' if no_actions else 'Some Laya decisions changed context. The measured token deltas include both policy effects and generation variability; see the trial traces for actual mutations.')
report = f'''# Coding experiments: tool filtering and post-tool rewind

{interpretation}

Thirty fresh coding trials covered three tasks, two repetitions and five configurations. The tasks were exact-decimal CSV parsing, HTTP retry scheduling and archive path normalization. Each had 16 hidden behavioral checks. Every trial started from known-buggy code and proceeded through a verbose log read, an unrelated read, a requirements read and implementation. No hidden-test feedback or repair attempt was given to the agent.

| Configuration | Entire task passes | Individual checks pass | Total input tokens | Input change vs baseline | Filtered results | Rewinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

Positive input change means more tokens. Input includes cached and uncached input across **every** model request, including the model calls that use tools. It excludes local Laya inference, which is reported separately. Cache reuse is not token removal. All trials used Pi 0.87.1, `openai-codex` subscription OAuth, `gpt-6-luna`, and the pinned 421M English Laya checkpoint on the local GPU.

## What was actually exercised

- Tool-result filtering called local Laya from Pi's `tool_result` event for large read outputs. `KEEP_RESULT` or `EXTERNALIZE` can produce an archived/excerpted result before the next model request. The conservative implementation retains `KEEP_FULL` and `DISCARD` outputs at this stage; it does not delete unseen tool results on a relevance vote alone.
- The post-tool path also scored read-only tool results with Laya. After the complete agent run settled, it judged the complete speculative tail again and could call `navigateTree(checkpoint, {{summarize: false}})`. It does **not** navigate in the middle of an active tool-call/result pair. Mutating calls protect the tail.
- Both mechanisms were enabled simultaneously in the two combined arms. The lower-threshold arm was exploratory; production defaults were unchanged.

## Accuracy and overhead

The pass rates above measure generated code with executable tests, not merely whether a final answer mentions the right facts. They apply to these small tasks only. With no Laya-driven collection, retained task accuracy does not establish that Laya would preserve accuracy under substantial pruning.

| Configuration | Output tokens | Uncached input | Cached input | Laya calls | Laya inference total | Mean trial wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{timing}

There were {len(failures)} interrupted provider attempts. They are preserved under `infrastructure-failures/` and were rerun from fresh workspaces with the same protocol and no test feedback. These attempts are excluded from the matched successful-completion token comparison; their usage remains in [the analysis data](results/coding-analysis.json).

## Positive control: does active collection work?

A separate six-trial control used fixture-aware deterministic decisions, **not Laya**. It deliberately excerpted the known diagnostic log and collected the known irrelevant read. It used identical task specifications, initial code, prompts and hidden tests.

- Input tokens: **{positive_input:,}**, versus **{base_input:,}** for baseline: **{positive_summary['inputSavingsPercent']:.2f}% fewer**.
- Task accuracy: **{positive_summary['taskPasses']}/6** complete tasks and **{positive_summary['testsPassed']}/{positive_summary['testsTotal']}** behavioral checks.
- Actual actions: **{positive_summary['filteredResults']}** filtered results and **{positive_summary['rewinds']}** rewinds.

This verifies the mechanism under active pruning in this synthetic workload. It is not a Laya result, not a general achievable savings estimate, and not an upper bound. The control knows which fixtures are disposable.

## Reproduce and inspect

```bash
npm run benchmark -- --out=results/new-coding-run --repeats=2
node --import tsx src/positive-control.ts results/new-coding-run results/new-positive-control
```

The original design, source hashes and frozen source are in [results/coding-factorial](results/coding-factorial). Each trial contains source code, hidden-test outcomes, all prompts/responses, token telemetry and local judge decisions. [Control artifacts](results/coding-positive-control) and [machine-readable aggregation](results/coding-analysis.json) are retained. `python3 benchmarks/analyze.py` regenerates this report for the recorded result directories.

The original [cache/retention report](REPORT.md) remains separate: its 97.3% cache-hit result establishes reuse after rewind, not a 97.3% reduction in tokens.
'''
(root / 'CODING_REPORT.md').write_text(report)
print(json.dumps(result, indent=2))

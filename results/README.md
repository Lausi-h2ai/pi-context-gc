# Experiment evidence

The release includes synthetic benchmark data, generated task workspaces, session traces, usage telemetry, local-judge decisions, and reports. Reports retain negative findings. These are exploratory studies, not a production accuracy or billing guarantee.

| Study | Evidence |
| --- | --- |
| Latest aggressive general benchmark: 8 tasks × 3 arms | [v3 report](general-v3-aggressive-r1/GENERAL_REPORT.md), [design](general-v3-aggressive-r1/design.json), [resume notes](general-v3-aggressive-r1/RESUME_NOTES.md) |
| Earlier safe general benchmark: same catalog | [v2 report](general-v2-r1/GENERAL_REPORT.md) |
| Initial general benchmark and smoke/pilot runs | `general-v1-r1/`, `general-pilot-two/`, `general-smoke-laya/` |
| Fixed-policy transfer pilot | [report](coding-unseen-fixed-pilot/REPORT.md) |
| Focused long synthetic task | [report](coding-long-focused/REPORT.md) |
| Original long synthetic task | [report](coding-long-composite/REPORT.md) |
| Aggressive coding pilot | [report](coding-aggressive-pilot/REPORT.md) |
| Cache reuse, retention judge, integration, filtering | [original report](../REPORT.md) |

V3 resumed across 26–27 September 2026. Failed provider attempts and executions affected by a duplicate runner are preserved under `infrastructure-failures/`, outside the completed run directory. They are excluded from the final paired report. See the resume notes for details. Each of the 24 final v3 trials has one session and no provider error.

The experiment `design.json` files pin source and fixture hashes. Publication edits change documentation and package metadata, but leave the v3 runner, policy, workers, evaluator, fixtures, and pinned Python requirements unchanged. Historical absolute workspace paths are retained so recorded messages and hashes remain auditable. They will differ on another machine.

The public release excludes the separate offline replay of a personal Codex session, local authentication files, runtime sessions outside the synthetic benchmarks, caches, and watcher logs. No model weights are included.

## Recompute

From the repository root, using Python 3.12:

```bash
python3 benchmarks/general-analysis/analyze.py results/general-v3-aggressive-r1
python3 benchmarks/general-analysis/analyze.py results/general-v2-r1
```

These commands need no model credentials and rewrite the generated reports. Do not point the analyzer at all of `results/`: it recursively discovers trial files, and that would mix protocols and archived attempts.

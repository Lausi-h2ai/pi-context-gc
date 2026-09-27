# Fixed-policy unseen-task pilot results

Three new task domains, five arms, one independent generation per task/arm. Full protocol: `benchmarks/UNSEEN-PILOT.md`. Frozen source hashes verified against pre-run `design.json`.

| Arm | Tasks pass | Cases pass | Total input | Cached | Uncached | Output | Input saving | Filters / rewinds | Wall seconds | Judge seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 2/3 | 31/37 | 80,564 | 44,032 | 36,532 | 2,196 | 0.00% | 0 / 0 | 96.4 | 0.0 |
| heuristic | 2/3 | 31/37 | 55,626 | 17,920 | 37,706 | 2,026 | 30.95% | 2 / 0 | 108.1 | 0.0 |
| filter | 3/3 | 37/37 | 79,603 | 45,056 | 34,547 | 1,953 | 1.19% | 0 / 0 | 103.1 | 3.9 |
| rewind | 3/3 | 37/37 | 78,151 | 46,592 | 31,559 | 2,000 | 3.00% | 0 / 3 | 106.6 | 7.4 |
| both | 3/3 | 37/37 | 78,175 | 42,496 | 35,679 | 1,990 | 2.97% | 0 / 3 | 99.0 | 8.0 |

## Observed result

The frozen Laya filter changed zero outputs across all three new tasks, including both Laya-filter arms. Its 1.19% lower token total and better pass count cannot be attributed to filtering. Rewind-only and combined each deleted three unrelated tangents and used about 3% less total input than baseline; this is a small observed difference, not a robust estimate of savings.

The deterministic heuristic changed two outputs and reduced total input 30.95%, while cached input fell from 44,032 to 17,920 and uncached input rose from 36,532 to 37,706 (+3.21%). Thus the large total-token reduction is not an uncached-token improvement. JSONL logs were unchanged by both filters.

Baseline and heuristic each failed six escaped-record cases (31/37 overall). Both generated a comparison between a single character and a two-backslash string, preventing escape handling. Laya filter-only passed despite no context changes, directly demonstrating generation variability. The heuristic retained every actionable diagnostic line, including the multiline input example; no observed diagnostic loss explains its failure.

Recommendation: do not enable the focused classifier filter generally on this evidence. There is no demonstrated filtering advantage over the simple heuristic here. Keep the rewind mechanism experimental; a separately registered long-session test could assess whether its small observed benefit grows under context bloat. Do not retune against these results and call the same tasks unseen again.

## Task-level effects

| Task | Arm | Input | Cached | Uncached | Filters | Rewinds | Passed |
|---|---|---:|---:|---:|---:|---:|---:|
| intervals | baseline | 29,261 | 15,360 | 13,901 | 0 | 0 | 14/14 |
| intervals | heuristic | 11,978 | 0 | 11,978 | 1 | 0 | 14/14 |
| intervals | filter | 29,181 | 17,920 | 11,261 | 0 | 0 | 14/14 |
| intervals | rewind | 28,917 | 17,920 | 10,997 | 0 | 1 | 14/14 |
| intervals | both | 28,792 | 17,920 | 10,872 | 0 | 1 | 14/14 |
| dependencies | heuristic | 29,256 | 17,920 | 11,336 | 0 | 0 | 10/10 |
| dependencies | filter | 29,230 | 17,920 | 11,310 | 0 | 0 | 10/10 |
| dependencies | rewind | 28,736 | 17,920 | 10,816 | 0 | 1 | 10/10 |
| dependencies | both | 28,628 | 15,360 | 13,268 | 0 | 1 | 10/10 |
| dependencies | baseline | 30,014 | 17,920 | 12,094 | 0 | 0 | 10/10 |
| records | filter | 21,192 | 9,216 | 11,976 | 0 | 0 | 13/13 |
| records | rewind | 20,498 | 10,752 | 9,746 | 0 | 1 | 13/13 |
| records | both | 20,755 | 9,216 | 11,539 | 0 | 1 | 13/13 |
| records | baseline | 21,289 | 10,752 | 10,537 | 0 | 0 | 7/13 |
| records | heuristic | 14,392 | 0 | 14,392 | 1 | 0 | 7/13 |

## Retention audit

Exact archives and retained tool messages were compared for every changed output. `retention-audit.json` records hashes and missing actionable lines.
- intervals-r1-heuristic: archive hash matches=True; retained message found=True; omitted actionable lines=[].
- records-r1-heuristic: archive hash matches=True; retained message found=True; omitted actionable lines=[].

## Interpretation limits

Token differences without recorded filtering or rewinds are generation variability, not demonstrated policy savings. All requests, including tool continuations, are counted. Laya runs locally; judge latency is included in wall time but is not provider input. No price conversion is made.

This is a short six-turn transfer pilot. It does not recreate a long stable cacheable prefix, production tool streams, or sustained context bloat. The JSONL task is a deliberate format outside the unchanged Laya filter gate. Contracts are repeated before implementation, which can mask diagnostic information loss. Hidden cases check return values and exception types but not input mutation. Agent isolation is instruction-level, not a filesystem sandbox. A single trial per cell does not support statistical superiority or a production safety claim.

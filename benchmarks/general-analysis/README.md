# Paired general coding analysis

`analyze.py` consumes a completed general coding run and writes two artifacts
inside that run:

```bash
python3 benchmarks/general-analysis/analyze.py results/my-general-run \
  --baseline baseline --treatments laya von deterministic --check-gate
```

The default output files are `general-analysis.json` and `GENERAL_REPORT.md`.
The analyzer discovers `*/result.json` below the run directory. A trial is
paired with another arm by `pairKey`, or by `task` plus `repetition` when
`pairKey` is omitted. A pair is valid only when each side has one completed
`result.json` and a numeric total input count.

## Runner contract

The runner should write these fields in every trial `result.json`. They are
deliberately flat so the analyzer stays independent from Pi's internal usage
objects.

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable trial directory and artifact identifier. |
| `task` | string | Fixed task identifier. |
| `repetition` | integer | Repetition within the task. |
| `stratum` | string, optional | Workload stratum such as `short` or `long`. Used for per-stratum savings and quality comparisons. |
| `arm` | string | `baseline`, `laya`, `von`, or a named control. |
| `pairKey` | string, optional | Stable key shared by all arms of one task/repetition. Defaults to `task::r<repetition>`. |
| `inputTotal` | number | All input tokens across every Pi model request, including cached input. |
| `inputUncached` | number | Uncached input tokens across every request. |
| `inputCached` | number | Cached input tokens across every request. |
| `outputTokens` | number | Output tokens across every request. |
| `requests` | integer | Number of Pi model requests. |
| `evaluation` | object | `{ "passed": number, "total": number, "success": boolean }`. `success` means every hidden check passed. |
| `error` | string or null | Provider or infrastructure error. Failed rows are retained in the report and excluded from completed totals. |
| `prunedResults` | integer | Number of tool-result context changes actually applied. This is an event count, not the number of judge votes. |
| `removedToolCharacters` | number | Characters removed from tool results by applied filtering. Use zero when no result changed. |
| `judgeCalls` | integer | Local Laya or Von judge calls, including votes that produced no context change. |
| `judgeLatencyMs` | number | Local judge time, reported separately from Pi wall time. |
| `wallMs` | number | End-to-end trial time. |

These optional fields improve diagnostics: `status`, `model`,
`initialEvaluation`, `rewinds`, and `prunedCharacters`. The initial evaluation
should fail on each fixture; the final evaluation is the quality metric.

`outcomes.json` may contain the same rows for convenience, but the analyzer
uses the per-trial files so an interrupted run can still identify missing or
invalid artifacts.

When `stratum` is omitted from a result, the analyzer looks for a `stratum`
field in that task's `design.json` metadata (and accepts `metadata.stratum` or
`length: "short"/"long"` as compatibility aliases). If no result or task
metadata supplies a stratum, the overall report remains valid and omits the
stratum tables.

## Ceiling analysis

`ceiling.py` measures what the context policy could remove on a run's workload,
independent of what the judge chose. It replays the baseline sessions, rebuilds
each request context, and sums the tool results the policy would accept as
candidates. The availability bound is the true upper bound on savings; see
[`CEILING.md`](../../CEILING.md) for the v2 result and its reading.

```bash
python3 benchmarks/general-analysis/ceiling.py results/general-v2-r1
```

## Payload trace

`trace.py` prints the request-by-request provider payload for one task across
the arms, which attributes a saving to a point in the conversation and exposes a
candidate that simply did more work than the baseline.

```bash
python3 benchmarks/general-analysis/trace.py results/general-v2-r1 record-sort
```

## Event logs

The result counters are the summary contract. The event logs make attribution
auditable:

* `context-events.jsonl` (the general runner's name) or
  `filter-events.jsonl` should record one object per applied filter attempt with
  `toolName`, `originalCharacters`, `retainedCharacters`, and an optional
  `changed` boolean and `action`. When `changed` is omitted, the analyzer
  derives it from the character counts. A true value means the next Pi request
  received a shorter or otherwise replaced tool result. A `DISCARD` vote with
  `changed: false` is a judgment, not a saving.
* `gc.jsonl` should record one object per completed-turn prune decision with
  `action`, `contextChanged`, `beforeMessages`, `afterMessages`, and an
  optional `removedCharacters`. The analyzer counts a prune only when
  `contextChanged` is true, the message count decreased, or the action is a
  known changing action such as `DROP`, `REWIND`, `NAVIGATE`, or `PRUNE`.
* `judge.jsonl` records local judge calls and latency. It is used to report
  policy overhead; votes do not count as filtering or pruning by themselves.

The analyzer also consumes the general runner's embedded `events` array. It
accepts the existing benchmark spellings `filteredResults` and `rewinds` as
aliases. For the general runner, `prunedResults` and explicit event fields are
preferred.

## What the report means

For every candidate, the report includes:

* pooled savings, paired mean and median savings, and a deterministic 95%
  percentile bootstrap interval for total, uncached, and cached input;
* the same savings and quality metrics split by each workload stratum, so a
  long-task gain cannot hide a short-task regression;
* total and per-case pass rates, paired task/case deltas, and an exact
  two-sided McNemar p-value for task pass discordance;
* counts of judge calls, applied filters, applied prunes, removed characters,
  cache share, cached request count, and wall time;
* a target gate and a quality guard.

The default target band is 25% to 35% total input savings. The default quality
guard allows no observed task pass loss and at most a two percentage point
hidden-case pass loss. Set these in `design.json` or override them with
`--min-savings`, `--max-savings`, `--max-task-drop`, and `--max-case-drop`.
Arguments can be percentages (`25`, `2`) or fractions (`0.25`, `0.02`).

`PASS` means the observed pooled total savings is inside the target band, the
quality guard passes for the overall pairs and every paired stratum, and at
least one filter or prune event was applied.
Every design-declared task/repetition must have exactly one valid baseline and
candidate artifact before a comparison can pass. A surviving subset is still
shown for diagnosis, but its gate is `INCOMPLETE` and its quality result is not
treated as a win.
`ABOVE_TARGET_BAND` means the same quality and attribution checks passed but
the observed savings exceeded 35%. `BELOW_TARGET`, `FAIL_QUALITY`,
`FAIL_NO_CONTEXT_CHANGES`, and `INCOMPLETE` identify why a candidate does not
meet the gate. The lower confidence bound is reported separately because a
small paired run may have a wide interval.

Cached tokens remain part of total input. A fall in cached input alone is not
treated as a context saving; the report shows cached and uncached changes
separately so cache warming and actual pruning can be distinguished.

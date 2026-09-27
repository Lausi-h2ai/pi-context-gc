# General benchmark artifact schema

This is the minimal schema expected by
[`analyze.py`](analyze.py). JSON numbers are nonnegative token or count
values unless the field name says otherwise. Additional fields are preserved
by the runner and do not affect aggregation.

## `design.json`

```json
{
  "schemaVersion": 1,
  "design": {
    "name": "general-coding-pi-harness",
    "repeats": 10,
    "arms": [
      {"name": "baseline", "role": "baseline", "model": "gpt-6-luna"},
      {"name": "laya", "role": "candidate", "model": "gpt-6-luna"},
      {"name": "von", "role": "candidate", "model": "gpt-6-luna"}
    ],
    "tasks": [
      {"id": "task-01", "stratum": "short", "tests": 16}
    ],
    "targetSavings": {"minPercent": 25, "maxPercent": 35},
    "qualityGuard": {"maxTaskPassDrop": 0, "maxCasePassDrop": 2}
  }
}
```

`design` may also be at the top level. The analyzer uses the arm names,
repeat count and task IDs to report expected completion. Arm roles are
descriptive; use `--treatments` when a control should be excluded from the
candidate gate.

## Trial `result.json`

```json
{
  "schemaVersion": 1,
  "id": "task-01-r0-laya",
  "task": "task-01",
  "repetition": 0,
  "stratum": "short",
  "pairKey": "task-01::r0",
  "arm": "laya",
  "model": "gpt-6-luna",
  "inputTotal": 10000,
  "inputUncached": 2800,
  "inputCached": 7200,
  "outputTokens": 500,
  "requests": 11,
  "evaluation": {"passed": 16, "total": 16, "success": true},
  "initialEvaluation": {"passed": 4, "total": 16, "success": false},
  "error": null,
  "prunedResults": 2,
  "removedToolCharacters": 18400,
  "judgeCalls": 14,
  "judgeLatencyMs": 2100,
  "wallMs": 43000
}
```

Use `error` for provider or infrastructure failures and keep the row on disk.
Do not turn a failed trial into a zero-token successful trial. The analyzer
reports it as invalid and excludes it from paired completed-trial metrics.

## JSONL events

The event files are optional for input accounting, but they are required for a
defensible attribution claim. The general runner writes
`context-events.jsonl` and embeds the same rows as `events` in `result.json`.
Older benchmark runs may use `filter-events.jsonl`. Example filter event:

```json
{
  "event": "tool-filter",
  "toolName": "read",
  "toolCallId": "call-1",
  "action": "KEEP_RESULT",
  "originalCharacters": 13000,
  "retainedCharacters": 700,
  "removedCharacters": 12300
}
```

Example deferred prune event:

```json
{
  "event": "completed-turn-prune",
  "action": "DROP",
  "contextChanged": true,
  "beforeMessages": 19,
  "afterMessages": 11,
  "removedCharacters": 28000,
  "reason": "disposable read-only tangent"
}
```

An event with a judge vote but `changed: false` or `contextChanged: false`
must remain in the log. It contributes to policy overhead and auditability,
but not to `prunedResults` or the actual context-change count.

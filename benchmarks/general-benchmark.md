# General coding benchmark catalog

`general-tasks.ts` is a host-side catalog for the Pi coding harness. Each task
contains a deliberately incomplete `solver.py`, a public contract, a realistic
initial failure fixture, a deterministic turn sequence, and hidden behavioral
cases. The runner writes `task.files` into a fresh workspace and calls
`evaluateGeneralTask(task, workspace)` only after the implementation turns have
settled.

The evaluator receives cases through stdin and never writes them into the
workspace. It launches a separate candidate process for each case and sends
that process only the function name and arguments. It compares JSON-like
results with strict scalar types, checks expected `ValueError` boundaries,
and checks that mutable arguments and nested source values were not changed.

## Catalog

| Task | Function | Domain | Hidden cases | Fixture stratum |
| --- | --- | --- | ---: | --- |
| `config-merge` | `merge_settings` | layered service configuration | 17 | long output |
| `header-redaction` | `redact_headers` | HTTP request logging | 15 | short realistic |
| `rate-window` | `admit_requests` | API admission control | 18 | long output |
| `pagination` | `paginate_records` | cursor based API pages | 18 | long output |
| `duration` | `parse_duration` | deployment configuration | 21 | short realistic |
| `dotenv` | `parse_env` | startup environment files | 22 | short realistic plus project guide |
| `record-sort` | `sort_records` | export/report ordering | 17 | long output |
| `canonical-url` | `canonical_url` | HTTP cache key generation | 19 | short realistic plus project guide |

The four long-output fixtures are an explicit context-volume stratum. Their
diagnostic files contain 150 deterministic informational lines followed by one
actionable failure. The four short fixtures contain six timestamped lines with
one actionable failure. `dotenv` and `canonical-url` also include a
repository-style `project-guide.md` and a context turn that reads it. This
keeps task diversity visible when results are aggregated: a reduction measured
only on the long stratum is log-volume evidence, while the short stratum tests
whether the policy changes ordinary coding sessions.

## Reproducibility and leakage controls

Task files are deterministic strings; they contain no timestamps generated at
runtime, network calls, or random values. `prepareGeneralWorkspace` is provided
for callers that want the same fixture-writing behavior as the runner. Hidden
cases remain in the TypeScript host process and are serialized only into the
evaluator's stdin. The initial source is checked by the evaluator and must fail
at least one hidden case before a trial is valid.

Do not add hidden expected values to requirements, diagnostics, project guides,
or the candidate workspace. Public contracts describe behavior sufficiently for
an independent implementation; diagnostics identify a realistic symptom and
the task turns require the agent to read the contract before editing.

## Interpretation limits

These are isolated Python functions in a temporary workspace, not complete
open-source repositories. They exercise common maintenance patterns—parsing,
validation, ordering, copy semantics, scheduling, and URL handling—but cannot
represent build systems, dependency upgrades, multi-file refactors, language
toolchains, or production traffic. Hidden-case accuracy therefore supports
these contracts only. Report total, cached, and uncached input separately, and
attribute token savings to a context policy only when its event trace records
an actual retained or pruned result.

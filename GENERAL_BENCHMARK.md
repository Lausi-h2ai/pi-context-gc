# Pi coding context benchmark

This benchmark runs the same coding tasks through three Pi session arms: no
context pruning, Laya-prioritized pruning, and Von-prioritized pruning. Each
arm receives a fresh workspace and the same scripted user turns. Hidden cases
are evaluated after editing and are never written into the agent workspace.

The catalog currently contains eight Python standard-library repair tasks.
Four have short diagnostic context; four intentionally stress long tool output.
These are controlled coding exercises, so results are evidence about this
workload rather than a production-wide token-saving estimate.

## Run

Install Node and Python dependencies, ensure Pi can use the existing
`openai-codex` subscription login, then run:

```bash
npm ci
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm run check
npm test
npm run benchmark:general -- --out=results/general-run --repeats=2
python3 benchmarks/general-analysis/analyze.py results/general-run --check-gate
```

Use `--tasks=config-merge,header-redaction` or
`--arms=baseline,laya` for a small integration run. The default Pi model is
`gpt-6-luna`; set `OPENAI_MODEL` to compare another subscription model. A
completed trial is reused when resuming the same output directory. Changing
task definitions, evaluator, policy, model, or dependencies requires a new
output directory because `design.json` pins their hashes.

The default `--policy=safe` uses a 1,500-character threshold and protects
contract, project-guide, and source reads. The exploratory
`--policy=aggressive` lowers the threshold to 600 characters and permits
project guides to be archived while still protecting requirements and source
reads. Use a fresh output directory for each policy.

## Policy and measurements

The default `context` extension considers text tool results of at least 1,500
characters from earlier turns after the next user message arrives. It keeps
`requirements.txt`, `project-guide.md`, and `solver.py` reads exact. It archives
other full results in the trial workspace and replaces selected results with a
readable path. Current-turn results stay intact. The fixed policy aims to
retain 70% of conversation characters at each request and uses the local
classifier to choose lower-value results first.
It can override `KEEP_FULL` when the budget is exceeded; the event log records
the classifier action for every replacement. This is a budget policy guided by
Laya or Von, rather than a pure classifier-vote policy.

The runner allows two provider transport retries for transient network
failures and records any trial that still fails. The primary token metric is
total Pi input across all model requests,
including cache reads and writes. The report also shows uncached input,
cached input, output, task and case pass rates, real context changes, and
judge time. A useful result requires task quality to hold; a low token count
on a failed repair is not a win. Compare the short and long strata separately
before interpreting the pooled result.

The default report gate checks for 25–35% pooled input savings, no task pass
loss, at most a two percentage point case pass loss, and evidence that context
actually changed. Paired uncertainty is shown separately. A single repeat
is a pilot; two or more repeats improve the estimate but do not turn this
synthetic catalog into a claim about all coding work.

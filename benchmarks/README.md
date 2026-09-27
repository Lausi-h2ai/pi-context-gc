# Coding benchmark protocol

Run `npm run benchmark -- --out=results/my-coding-run --repeats=2` from the repository root.

For the aggressive follow-up, run `npm run benchmark:aggressive -- --out=results/my-aggressive-run --repeats=1` and `python3 benchmarks/analyze_aggressive.py results/my-aggressive-run`. This is a separate, newly hashed design with fresh baseline trials. Laya judges each roughly 1,600-character diagnostic-log chunk; `KEEP_RESULT` preserves actionable lines, and `DISCARD` omits the chunk while preserving any explicit failure line. Every full output is archived. A completed read-only turn can rewind at a 0.50 threshold when every tool result votes `DISCARD` and the whole-turn judgment is `KEEP_RESULT` or `DISCARD`. The benchmark measures actual context changes and hidden-test accuracy. These policy choices were developed using the three existing synthetic diagnostic logs, so the run evaluates coding behavior under pruning on those logs, not generalization to unseen log formats.

For the longer cache-focused run, use `npm run benchmark:long -- --out=results/my-long-run --repeats=2`, then `python3 benchmarks/analyze_aggressive.py results/my-long-run`. Each trial repairs all three functions in one module against 48 hidden cases. Before editing, Pi reads a stable 20,109-character task contract, three 13,084-character diagnostic logs, three unrelated notes, and a concise requirements file over eleven turns. The stable reference makes repeated requests eligible for prefix caching while later logs and detours create avoidable context. Paired baseline and aggressive arms use the same prompts and fresh workspaces. Report cached and uncached input separately; a drop in cached tokens alone is not a reduction in uncached usage. This is still a controlled synthetic workload rather than a reproduction of a 10-million-cached-token production session.

The follow-up `npm run benchmark:long-focused -- --out=results/my-long-focused-run --repeats=2` keeps the same workload but asks Laya to judge each diagnostic against the relevant function's objective and reduces the experimental rewind gate from 0.50 to 0.30. This policy was chosen after inspecting the first long run and probing its log format, so it is a development comparison on known synthetic inputs, not independent validation. Analyze it with the same script and view it with `npm run dashboard -- --results=results/my-long-focused-run --control=none --port=8768`.

The [fixed-policy transfer pilot](UNSEEN-PILOT.md) runs with `npm run benchmark:unseen -- --out=results/my-unseen-run --repeats=1`. It compares that frozen Laya policy with a simple deterministic log filter and separate filter/rewind arms on three new coding tasks. The [completed pilot report](../results/coding-unseen-fixed-pilot/REPORT.md) includes per-task accuracy, cache usage, actual context changes, and an exact-output retention audit.

Inspect the recorded run with `npm run dashboard` and open `http://127.0.0.1:8765`. The viewer refreshes every five seconds and excludes provider-error trials from its valid totals. The original conservative run was interrupted by provider errors and is preserved as historical evidence. New protocols use new output directories with their own design hashes.

The design is written before execution to `design.json`, including hashes of fixtures and policy code. Existing completed trials can be resumed only with the same design. Nothing is tuned against the results during a run.

Three tasks repair a Python module: exact decimal CSV parsing, bounded HTTP retry scheduling, and archive member path normalization. Each has 16 separately graded behavior cases. Every trial begins with identical buggy source for its task; the evaluator checks that it initially fails. Cases stay outside the model's workspace and arrive at the evaluator over stdin. The model receives requirements, not hidden tests, and gets no repair attempt after evaluation.

Each trial has five stages: task introduction, a verbose diagnostic read, an unrelated read, a requirements read, and implementation. The model has read, write and edit tools in an isolated workspace. Tool filtering can classify large read outputs; post-tool GC classifies read-only results and then checks the full speculative tail after the run settles. Code changes are protected against rewind by the existing side-effect policy.

| Arm | Tool-result filtering | Post-tool judgment and deferred rewind |
| --- | --- | --- |
| baseline | Off | Off |
| filter | On | Off |
| rewind | Off | On, 0.95 threshold |
| both | On | On, 0.95 threshold |
| both-exploratory | On | On, 0.50 threshold |

Two repetitions produce 30 trials. Arm order rotates by task and repetition. Model generations are independent, so token-count differences can include response-length and tool-call variability. Report actual filter and rewind counts alongside token differences: if neither changes context, a lower observed count cannot be attributed to collection.

Primary metrics are total input tokens across **all** model calls and the fraction of implementations passing **all** hidden tests. Secondary metrics include test-case pass rate, cached versus uncached input, output tokens, local judge calls/time, wall time and actual context mutations. Cache hits count as input tokens; they are not removed tokens. Subscription accounting is not converted to estimated dollars.

These are small, controlled tasks with synthetic logs and explicit tangents. Repeating three tasks is not a representative benchmark of real repositories. A result such as 6/6 task passes is evidence only for those six executions, not proof of unchanged general coding accuracy.

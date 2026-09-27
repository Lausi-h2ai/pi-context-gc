# Long-session Laya coding pilot

One three-function composite coding task, 2 paired executions per arm, and 48 hidden behavioral checks per trial. Each trial read a stable contract, three verbose diagnostics, and three unrelated notes before implementation. Baseline and aggressive trials used fresh workspaces and independent model generations.

| Arm | Complete tasks | Hidden checks | Total input | Uncached input | Cached input | Output | Requests | Filtered results | Rewinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 2/2 | 96/96 | 393,211 | 60,411 | 332,800 | 3,264 | 43 | 0 | 0 |
| Aggressive Laya | 2/2 | 96/96 | 249,879 | 37,911 | 211,968 | 3,341 | 42 | 6 | 6 |

The aggressive arm used **36.45% fewer input tokens** across all model requests, counting cached and uncached tokens. It removed 57,254 tool-output characters. Laya made 88 local judgments. Cached input changed by -120,832 tokens, and uncached input by -22,500 tokens. Token differences also include independent generation variability; actual filters and rewinds identify context changes.

The output filter was developed using these synthetic diagnostic-log formats before this run. This pilot tests whether Pi still solves the tasks after pruning; it does not establish performance on unseen repositories or log formats. Exact archived outputs, Laya scores, Pi turns and usage are in the per-trial directories.

This focused policy was chosen after inspecting the first long run and probing the same synthetic log format. Its result is developmental and needs validation on unseen tasks and logs.

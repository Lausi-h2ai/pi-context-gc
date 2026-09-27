# Long-session Laya coding pilot

One three-function composite coding task, 2 paired executions per arm, and 48 hidden behavioral checks per trial. Each trial read a stable contract, three verbose diagnostics, and three unrelated notes before implementation. Baseline and aggressive trials used fresh workspaces and independent model generations.

| Arm | Complete tasks | Hidden checks | Total input | Uncached input | Cached input | Output | Requests | Filtered results | Rewinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 2/2 | 96/96 | 382,530 | 68,674 | 313,856 | 3,058 | 42 | 0 | 0 |
| Aggressive Laya | 2/2 | 96/96 | 384,364 | 56,684 | 327,680 | 3,104 | 42 | 6 | 0 |

The aggressive arm used **0.48% more input tokens** across all model requests, counting cached and uncached tokens. It removed 726 tool-output characters. Laya made 88 local judgments. Cached input changed by +13,824 tokens, and uncached input by -11,990 tokens. Token differences also include independent generation variability; actual filters and rewinds identify context changes.

The output filter was developed using these synthetic diagnostic-log formats before this run. This pilot tests whether Pi still solves the tasks after pruning; it does not establish performance on unseen repositories or log formats. Exact archived outputs, Laya scores, Pi turns and usage are in the per-trial directories.

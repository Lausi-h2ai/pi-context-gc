# Aggressive Laya coding pilot

Three coding tasks, 3 paired executions per arm, and 16 hidden behavioral checks per task. Baseline and aggressive trials used fresh workspaces and independent model generations.

| Arm | Complete tasks | Hidden checks | Total input | Uncached input | Cached input | Filtered results | Rewinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 3/3 | 48/48 | 77,968 | 24,208 | 53,760 | 0 | 0 |
| Aggressive Laya | 3/3 | 48/48 | 31,174 | 31,174 | 0 | 3 | 3 |

The aggressive arm used **60.02% fewer input tokens** across all model requests, counting cached and uncached tokens. It removed 33,364 tool-output characters. Laya made 45 local judgments. Token differences also include independent generation variability; actual filters and rewinds identify context changes.

**Cache tradeoff:** uncached input increased by 6,966 tokens, while reported cached input fell by 53,760 tokens. The shorter aggressive requests received no reported cache hits in this run. This pilot establishes fewer total context tokens, not fewer uncached tokens or lower subscription quota use.

See [the request-level cache analysis](CACHE_ANALYSIS.md) for the stable request fields, timing of the first misses, and a separate no-rewind prompt-length probe.

The output filter was developed using these synthetic diagnostic-log formats before this run. This pilot tests whether Pi still solves the tasks after pruning; it does not establish performance on unseen repositories or log formats. Exact archived outputs, Laya scores, Pi turns and usage are in the per-trial directories.

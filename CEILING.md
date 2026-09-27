# Context availability analysis

This analysis asks how much text the policy could remove from recorded baseline conversations. It complements the paired benchmark reports, which measure what independently generated candidate sessions actually used.

```bash
python3 benchmarks/general-analysis/ceiling.py results/general-v2-r1
```

The script reconstructs baseline contexts and counts eligible text tool results from earlier turns, respecting protected reads and minimum lengths. Availability is an upper bound on removable eligible characters in that fixed baseline trace. It is **not a hard ceiling on token savings in a new agent run**: characters only approximate tokens, archive notices consume space, cached prefixes can change, and the agent may take more or fewer requests or reread an artifact.

## Recorded v2 baseline availability

| Stratum | Trials | Safe availability | Safe at 0.70 retained fraction | Aggressive availability | Aggressive at 0.70 retained fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| long | 4 | 56.3% | 28.0% | 56.3% | 28.0% |
| short | 4 | 0.0% | 0.0% | 8.6% | 8.5% |
| ALL | 8 | 30.8% | 15.3% | 34.7% | 19.2% |

The budget removes whole candidates and can overshoot its target. These columns describe a replay of baseline messages; the candidate conversations do not necessarily contain the same messages or requests.

The v2 long tasks provided much more eligible text than the short tasks. `duration` and `header-redaction` had zero eligible content under both thresholds; `canonical-url` and `dotenv` had zero under the safe threshold. Short-task token differences under that policy therefore do not demonstrate pruning gains.

## Agent behavior can dominate the outcome

| Task | Arm | Requests | Total input | Savings | Removed characters |
| --- | --- | ---: | ---: | ---: | ---: |
| config-merge | baseline | 17 | 61,319 | — | 0 |
| config-merge | laya | 14 | 24,950 | 59.3% | 12,796 |
| config-merge | von | 13 | 22,452 | 63.4% | 12,797 |
| record-sort | baseline | 18 | 69,578 | — | 0 |
| record-sort | laya | 22 | 84,309 | -21.2% | 34,797 |
| record-sort | von | 20 | 60,766 | 12.7% | 23,200 |
| pagination | baseline | 17 | 66,801 | — | 0 |
| pagination | von | 20 | 63,366 | 5.1% | 23,472 |

Laya's record-sort run removed substantial text but used more input overall. A count of removed characters cannot substitute for total usage and task quality.

The removal budget did not stop candidate processing in any of the 16 completed v2 treatment trials: each judged candidate was applied. Lowering the retained fraction alone therefore has little supporting evidence as the next intervention on these recorded trials.

## Run-to-run variation

The first three completed v3 baselines showed the following availability compared with v2:

| Task | Stratum | v2 availability | v3 availability |
| --- | --- | ---: | ---: |
| config-merge | long | 61.9% | 54.3% |
| rate-window | long | 56.4% | 66.2% |
| header-redaction | short | 0.0% | 0.0% |

That is consistent with more removable text in the long-task fixtures, but each entry comes from one baseline session. Input totals also varied considerably: config-merge went from 61,319 to 98,202 tokens and rate-window from 60,754 to 111,822. The v3 run encountered provider quota problems, and independent model behavior and retries can both affect usage.

V3 is now complete; see its [report](results/general-v3-aggressive-r1/GENERAL_REPORT.md) and [resume provenance](results/general-v3-aggressive-r1/RESUME_NOTES.md). Its observed pooled savings exceed the v2 fixed-trace availability proxy, which is another reason not to treat that proxy as a universal bound.

## Interpretation and correction

An earlier version of this note called the pooled 25–35% target unreachable. The data do **not** prove that: a 34.7% availability estimate overlaps that band, and a baseline character replay does not bound new agent trajectories. The supported conclusion is that the safe catalog has little pruning opportunity on short tasks and that one repetition cannot isolate modest policy effects from agent variability.

Next steps are a deterministic archiving control under identical eligibility and budget rules, repeated trials with balanced arm order, and an unseen task set. Report total input, cached and uncached input, requests, elapsed time, and quality together. Judge quality and policy effectiveness remain separate empirical questions.

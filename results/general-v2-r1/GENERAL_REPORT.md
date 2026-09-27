# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 24 discovered, 24 valid, 0 incomplete or failed, 0 expected pair artifacts missing, 0 expected arm/pair entries invalid or incomplete.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8/8 | 7/8 (87.5%) | 146/147 (99.3%) | 453,482 | 146,794 | 306,688 | 0 | 0 | 67.6% |
| laya | 8/8 | 7/8 (87.5%) | 146/147 (99.3%) | 419,221 | 180,117 | 239,104 | 6 | 0 | 57.0% |
| von | 8/8 | 7/8 (87.5%) | 146/147 (99.3%) | 361,314 | 161,634 | 199,680 | 7 | 0 | 55.3% |

## Arm totals by stratum

Strata come from `result.stratum`; when a result omits it, the analyzer uses the task metadata in `design.json`.

| Stratum | Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| long | baseline | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 258,452 | 71,572 | 186,880 |
| long | laya | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 172,970 | 90,026 | 82,944 |
| long | von | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 173,870 | 82,222 | 91,648 |
| short | baseline | 4/4 | 4/4 (100%) | 77/77 (100%) | 195,030 | 75,222 | 119,808 |
| short | laya | 4/4 | 4/4 (100%) | 77/77 (100%) | 246,251 | 90,091 | 156,160 |
| short | von | 4/4 | 4/4 (100%) | 77/77 (100%) | 187,444 | 79,412 | 108,032 |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 6 | `{"KEEP_FULL": 6}` | `{}` |
| von | 7 | `{"KEEP_FULL": 7}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 8 | +7.56% [-47.25%, +36.44%] | -22.70% | +22.04% | +0.00% | +0.00% | 6/0 | **BELOW_TARGET** |
| von | 8 | +20.32% [-9.39%, +37.21%] | -10.11% | +34.89% | +0.00% | +0.00% | 7/0 | **BELOW_TARGET** |

## Paired comparisons by stratum

This breakdown keeps task/repetition pairing within each stratum. It exposes whether a short-task or long-task result drives the overall estimate.

| Stratum | Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| long | laya | 4 | +33.07% | -25.78% | +55.62% | +0.00% | +0.00% | **PASS** |
| long | von | 4 | +32.73% | -14.88% | +50.96% | +0.00% | +0.00% | **PASS** |
| short | laya | 4 | -26.26% | -19.77% | -30.34% | +0.00% | +0.00% | **FAIL_NO_CONTEXT_CHANGES** |
| short | von | 4 | +3.89% | -5.57% | +9.83% | +0.00% | +0.00% | **BELOW_TARGET** |

## Quality guard and cache effects

### laya

Task pass rate: 87.5% baseline versus 87.5% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; overall quality guard: PASS; stratum quality guard: PASS.
Cache share: 67.6% baseline versus 57.0% candidate; cached input delta -67,584 tokens and uncached input delta 33,323 tokens.
Target gate: **BELOW_TARGET**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

### von

Task pass rate: 87.5% baseline versus 87.5% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; overall quality guard: PASS; stratum quality guard: PASS.
Cache share: 67.6% baseline versus 55.3% candidate; cached input delta -107,008 tokens and uncached input delta 14,840 tokens.
Target gate: **BELOW_TARGET**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

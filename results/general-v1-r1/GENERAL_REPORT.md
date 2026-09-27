# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 24 discovered, 22 valid, 2 incomplete or failed, 0 expected pair artifacts missing, 2 expected arm/pair entries invalid or incomplete.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 7/8 | 5/7 (71.4%) | 126/128 (98.4%) | 463,965 | 142,941 | 321,024 | 0 | 0 | 69.2% |
| laya | 8/8 | 5/8 (62.5%) | 144/147 (98.0%) | 249,357 | 145,421 | 103,936 | 14 | 0 | 41.7% |
| von | 7/8 | 6/7 (85.7%) | 127/128 (99.2%) | 303,980 | 160,108 | 143,872 | 15 | 0 | 47.3% |

## Arm totals by stratum

Strata come from `result.stratum`; when a result omits it, the analyzer uses the task metadata in `design.json`.

| Stratum | Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| long | baseline | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 312,356 | 78,372 | 233,984 |
| long | laya | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 126,339 | 73,091 | 53,248 |
| long | von | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 175,685 | 98,373 | 77,312 |
| short | baseline | 3/4 | 2/3 (66.7%) | 57/58 (98.3%) | 151,609 | 64,569 | 87,040 |
| short | laya | 4/4 | 2/4 (50%) | 75/77 (97.4%) | 123,018 | 72,330 | 50,688 |
| short | von | 3/4 | 3/3 (100%) | 58/58 (100%) | 128,295 | 61,735 | 66,560 |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 14 | `{"KEEP_FULL": 10, "KEEP_RESULT": 4}` | `{}` |
| von | 15 | `{"EXTERNALIZE": 3, "KEEP_FULL": 11, "KEEP_RESULT": 1}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 7 | +53.70% [+26.86%, +61.45%] | +12.03% | +72.25% | +0.00% | -0.03% | 12/0 | **INCOMPLETE** |
| von | 7 | +34.48% [-20.49%, +50.03%] | -12.01% | +55.18% | +14.29% | +0.65% | 15/0 | **INCOMPLETE** |

## Paired comparisons by stratum

This breakdown keeps task/repetition pairing within each stratum. It exposes whether a short-task or long-task result drives the overall estimate.

| Stratum | Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| long | laya | 4 | +59.55% | +6.74% | +77.24% | +0.00% | +0.00% | **ABOVE_TARGET_BAND** |
| long | von | 4 | +43.75% | -25.52% | +66.96% | +0.00% | +0.00% | **ABOVE_TARGET_BAND** |
| short | laya | 3 | +41.63% | +18.46% | +58.82% | +0.00% | -0.07% | **INCOMPLETE** |
| short | von | 3 | +15.38% | +4.39% | +23.53% | +33.33% | +1.52% | **INCOMPLETE** |

## Quality guard and cache effects

### laya

Task pass rate: 71.4% baseline versus 71.4% candidate (+0.00%). McNemar discordance: 1 candidate wins, 1 losses, p=1.
Case pass rate delta: -0.03%; overall quality guard: INCOMPLETE; stratum quality guard: INCOMPLETE.
Cache share: 69.2% baseline versus 41.5% candidate; cached input delta -231,936 tokens and uncached input delta -17,200 tokens.
Target gate: **INCOMPLETE**. Observed band=False, conservative lower bound at least minimum=True, mechanism evidence=True.

### von

Task pass rate: 71.4% baseline versus 85.7% candidate (+14.29%). McNemar discordance: 1 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.65%; overall quality guard: INCOMPLETE; stratum quality guard: INCOMPLETE.
Cache share: 69.2% baseline versus 47.3% candidate; cached input delta -177,152 tokens and uncached input delta 17,167 tokens.
Target gate: **INCOMPLETE**. Observed band=True, conservative lower bound at least minimum=False, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

Incomplete artifacts:

- `canonical-url-r1-baseline`: Error: fetch failed
- `canonical-url-r1-von`: Error: fetch failed

Invalid or incomplete expected arm/pair entries:

- `baseline` / `canonical-url::r0`: invalid
- `von` / `canonical-url::r0`: invalid

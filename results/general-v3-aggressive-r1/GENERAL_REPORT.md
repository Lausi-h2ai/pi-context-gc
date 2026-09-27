# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 24 discovered, 24 valid, 0 incomplete or failed, 0 expected pair artifacts missing, 0 expected arm/pair entries invalid or incomplete.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8/8 | 7/8 (87.5%) | 138/147 (93.9%) | 529,263 | 152,943 | 376,320 | 0 | 0 | 71.1% |
| laya | 8/8 | 7/8 (87.5%) | 146/147 (99.3%) | 293,319 | 162,759 | 130,560 | 8 | 0 | 44.5% |
| von | 8/8 | 6/8 (75%) | 145/147 (98.6%) | 301,038 | 157,678 | 143,360 | 8 | 0 | 47.6% |

## Arm totals by stratum

Strata come from `result.stratum`; when a result omits it, the analyzer uses the task metadata in `design.json`.

| Stratum | Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| long | baseline | 4/4 | 3/4 (75%) | 61/70 (87.1%) | 321,638 | 74,342 | 247,296 |
| long | laya | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 148,503 | 83,479 | 65,024 |
| long | von | 4/4 | 3/4 (75%) | 69/70 (98.6%) | 147,953 | 79,345 | 68,608 |
| short | baseline | 4/4 | 4/4 (100%) | 77/77 (100%) | 207,625 | 78,601 | 129,024 |
| short | laya | 4/4 | 4/4 (100%) | 77/77 (100%) | 144,816 | 79,280 | 65,536 |
| short | von | 4/4 | 3/4 (75%) | 76/77 (98.7%) | 153,085 | 78,333 | 74,752 |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 8 | `{"KEEP_FULL": 8}` | `{}` |
| von | 8 | `{"EXTERNALIZE": 3, "KEEP_FULL": 5}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 8 | +44.58% [+17.37%, +53.92%] | -6.42% | +65.31% | +0.00% | +5.88% | 8/0 | **ABOVE_TARGET_BAND** |
| von | 8 | +43.12% [+26.19%, +51.36%] | -3.10% | +61.90% | -12.50% | +5.31% | 8/0 | **FAIL_QUALITY_STRATUM** |

## Paired comparisons by stratum

This breakdown keeps task/repetition pairing within each stratum. It exposes whether a short-task or long-task result drives the overall estimate.

| Stratum | Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| long | laya | 4 | +53.83% | -12.29% | +73.71% | +0.00% | +11.76% | **ABOVE_TARGET_BAND** |
| long | von | 4 | +54.00% | -6.73% | +72.26% | +0.00% | +11.76% | **ABOVE_TARGET_BAND** |
| short | laya | 4 | +30.25% | -0.86% | +49.21% | +0.00% | +0.00% | **PASS** |
| short | von | 4 | +26.27% | +0.34% | +42.06% | -25.00% | -1.14% | **FAIL_QUALITY** |

## Quality guard and cache effects

### laya

Task pass rate: 87.5% baseline versus 87.5% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +5.88%; overall quality guard: PASS; stratum quality guard: PASS.
Cache share: 71.1% baseline versus 44.5% candidate; cached input delta -245,760 tokens and uncached input delta 9,816 tokens.
Target gate: **ABOVE_TARGET_BAND**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

### von

Task pass rate: 87.5% baseline versus 75% candidate (-12.50%). McNemar discordance: 0 candidate wins, 1 losses, p=1.
Case pass rate delta: +5.31%; overall quality guard: FAIL; stratum quality guard: FAIL.
Cache share: 71.1% baseline versus 47.6% candidate; cached input delta -232,960 tokens and uncached input delta 4,735 tokens.
Target gate: **FAIL_QUALITY_STRATUM**. Observed band=False, conservative lower bound at least minimum=True, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

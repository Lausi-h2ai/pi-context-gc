# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 6 discovered, 6 valid, 0 incomplete or failed, 0 expected pair artifacts missing.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 2/2 | 2/2 (100%) | 32/32 (100%) | 125,751 | 40,247 | 85,504 | 0 | 0 | 68.0% |
| laya | 2/2 | 2/2 (100%) | 32/32 (100%) | 58,022 | 34,470 | 23,552 | 3 | 0 | 40.6% |
| von | 2/2 | 2/2 (100%) | 32/32 (100%) | 94,842 | 45,178 | 49,664 | 5 | 0 | 52.4% |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 3 | `{"KEEP_FULL": 3}` | `{}` |
| von | 5 | `{"KEEP_FULL": 3, "KEEP_RESULT": 2}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 2 | +53.86% [-26.96%, +75.25%] | +14.35% | +72.46% | +0.00% | +0.00% | 3/0 | **ABOVE_TARGET_BAND** |
| von | 2 | +24.58% [-15.56%, +35.20%] | -12.25% | +41.92% | +0.00% | +0.00% | 5/0 | **BELOW_TARGET** |

## Quality guard and cache effects

### laya

Task pass rate: 100% baseline versus 100% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; quality guard: PASS.
Cache share: 68.0% baseline versus 40.6% candidate; cached input delta -61,952 tokens and uncached input delta -5,777 tokens.
Target gate: **ABOVE_TARGET_BAND**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

### von

Task pass rate: 100% baseline versus 100% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; quality guard: PASS.
Cache share: 68.0% baseline versus 52.4% candidate; cached input delta -35,840 tokens and uncached input delta 4,931 tokens.
Target gate: **BELOW_TARGET**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

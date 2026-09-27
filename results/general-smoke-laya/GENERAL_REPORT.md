# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 2 discovered, 2 valid, 0 incomplete or failed, 0 expected pair artifacts missing.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1/1 | 0/1 (0%) | 13/15 (86.7%) | 48,993 | 13,665 | 35,328 | 0 | 0 | 72.1% |
| laya | 1/1 | 0/1 (0%) | 13/15 (86.7%) | 24,781 | 17,101 | 7,680 | 1 | 0 | 31.0% |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 1 | `{"KEEP_FULL": 1}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 1 | +49.42% [+49.42%, +49.42%] | -25.14% | +78.26% | +0.00% | +0.00% | 1/0 | **ABOVE_TARGET_BAND** |

## Quality guard and cache effects

### laya

Task pass rate: 0% baseline versus 0% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; quality guard: PASS.
Cache share: 72.1% baseline versus 31.0% candidate; cached input delta -27,648 tokens and uncached input delta 3,436 tokens.
Target gate: **ABOVE_TARGET_BAND**. Observed band=False, conservative lower bound at least minimum=True, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

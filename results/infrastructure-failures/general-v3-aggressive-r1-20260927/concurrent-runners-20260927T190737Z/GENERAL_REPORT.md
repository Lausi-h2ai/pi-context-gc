# General coding Pi benchmark analysis

This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.

Artifacts: 24 discovered, 9 valid, 15 incomplete or failed, 0 expected pair artifacts missing, 15 expected arm/pair entries invalid or incomplete.
Target band: 25% to 35% total input savings; quality guard allows at most 0 percentage points of task pass loss and 2 points of case pass loss.

## Arm totals

| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 3/8 | 3/3 (100%) | 50/50 (100%) | 240,263 | 57,991 | 182,272 | 0 | 0 | 75.9% |
| laya | 3/8 | 3/3 (100%) | 50/50 (100%) | 124,200 | 63,784 | 60,416 | 3 | 0 | 48.6% |
| von | 3/8 | 3/3 (100%) | 50/50 (100%) | 103,504 | 53,840 | 49,664 | 3 | 0 | 48.0% |

## Arm totals by stratum

Strata come from `result.stratum`; when a result omits it, the analyzer uses the task metadata in `design.json`.

| Stratum | Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| long | baseline | 2/4 | 2/2 (100%) | 35/35 (100%) | 210,024 | 41,064 | 168,960 |
| long | laya | 2/4 | 2/2 (100%) | 35/35 (100%) | 97,013 | 47,349 | 49,664 |
| long | von | 2/4 | 2/2 (100%) | 35/35 (100%) | 77,281 | 37,857 | 39,424 |
| short | baseline | 1/4 | 1/1 (100%) | 15/15 (100%) | 30,239 | 16,927 | 13,312 |
| short | laya | 1/4 | 1/1 (100%) | 15/15 (100%) | 27,187 | 16,435 | 10,752 |
| short | von | 1/4 | 1/1 (100%) | 15/15 (100%) | 26,223 | 15,983 | 10,240 |

## Intervention actions

These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.

| Arm | Applied intervention events | Filter action counts | Prune action counts |
| --- | ---: | --- | --- |
| baseline | 0 | `{}` | `{}` |
| laya | 3 | `{"KEEP_FULL": 3}` | `{}` |
| von | 3 | `{"KEEP_FULL": 3}` | `{}` |

## Paired comparisons

Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.

| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya | 3 | +48.31% [+10.09%, +69.00%] | -9.99% | +66.85% | +0.00% | +0.00% | 3/0 | **INCOMPLETE** |
| von | 3 | +56.92% [+13.28%, +77.09%] | +7.16% | +72.75% | +0.00% | +0.00% | 3/0 | **INCOMPLETE** |

## Paired comparisons by stratum

This breakdown keeps task/repetition pairing within each stratum. It exposes whether a short-task or long-task result drives the overall estimate.

| Stratum | Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| long | laya | 2 | +53.81% | -15.31% | +70.61% | +0.00% | +0.00% | **INCOMPLETE** |
| long | von | 2 | +63.20% | +7.81% | +76.67% | +0.00% | +0.00% | **INCOMPLETE** |
| short | laya | 1 | +10.09% | +2.91% | +19.23% | +0.00% | +0.00% | **INCOMPLETE** |
| short | von | 1 | +13.28% | +5.58% | +23.08% | +0.00% | +0.00% | **INCOMPLETE** |

## Quality guard and cache effects

### laya

Task pass rate: 100% baseline versus 100% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; overall quality guard: INCOMPLETE; stratum quality guard: INCOMPLETE.
Cache share: 75.9% baseline versus 48.6% candidate; cached input delta -121,856 tokens and uncached input delta 5,793 tokens.
Target gate: **INCOMPLETE**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

### von

Task pass rate: 100% baseline versus 100% candidate (+0.00%). McNemar discordance: 0 candidate wins, 0 losses, p=1.
Case pass rate delta: +0.00%; overall quality guard: INCOMPLETE; stratum quality guard: INCOMPLETE.
Cache share: 75.9% baseline versus 48.0% candidate; cached input delta -132,608 tokens and uncached input delta -4,151 tokens.
Target gate: **INCOMPLETE**. Observed band=False, conservative lower bound at least minimum=False, mechanism evidence=True.

## Interpretation

A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.

The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.

Incomplete artifacts:

- `canonical-url-r1-baseline`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~184 min.
- `canonical-url-r1-laya`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~184 min.
- `canonical-url-r1-von`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~184 min.
- `dotenv-r1-baseline`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `dotenv-r1-laya`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `dotenv-r1-von`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `duration-r1-baseline`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `duration-r1-laya`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `duration-r1-von`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `pagination-r1-baseline`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~186 min.
- `pagination-r1-laya`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~186 min.
- `pagination-r1-von`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~186 min.
- `record-sort-r1-baseline`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~185 min.
- `record-sort-r1-laya`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~184 min.
- `record-sort-r1-von`: Error: You have hit your ChatGPT usage limit (plus plan). Try again in ~184 min.

Invalid or incomplete expected arm/pair entries:

- `baseline` / `pagination::r0`: invalid
- `baseline` / `duration::r0`: invalid
- `baseline` / `dotenv::r0`: invalid
- `baseline` / `record-sort::r0`: invalid
- `baseline` / `canonical-url::r0`: invalid
- `laya` / `pagination::r0`: invalid
- `laya` / `duration::r0`: invalid
- `laya` / `dotenv::r0`: invalid
- `laya` / `record-sort::r0`: invalid
- `laya` / `canonical-url::r0`: invalid
- `von` / `pagination::r0`: invalid
- `von` / `duration::r0`: invalid
- `von` / `dotenv::r0`: invalid
- `von` / `record-sort::r0`: invalid
- `von` / `canonical-url::r0`: invalid

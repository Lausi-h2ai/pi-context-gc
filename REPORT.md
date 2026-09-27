# Experiment report — 26 September 2026

**Pi rewind preserved cached input through the OpenAI subscription backend. The unmodified English Laya model did not provide useful automatic collection at the conservative threshold.**

Environment: Pi SDK 0.87.1, `openai-codex` provider, `gpt-6-luna`, existing ChatGPT subscription OAuth, SSE transport, Node 24.15.0. Local judge: `convaiinnovations/laya` revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, 421,293,827 parameters, Laya 0.3.20, PyTorch 2.14.0+cu130, NVIDIA RTX 3070. No hosted Jev endpoint was used.

## 1. Prompt cache after rewind

The runner built a synthetic project reference, warmed it, added five tangents, navigated back to the durable assistant checkpoint, and continued. It recorded hashes of actual rendered request fields and Pi's normalized backend usage.

| Request | Total input tokens | Cached tokens |
| --- | ---: | ---: |
| Cold reference | 17,611 | 0 |
| Warm reference | 17,632 | 17,152 |
| Fifth tangent | 19,762 | 19,200 |
| First continuation after rewind | 17,635 | 17,152 |
| Second continuation after rewind | 17,639 | 17,152 |
| Third continuation after rewind | 17,639 | 17,152 |
| Changed system-prefix control | 17,684 | 0 |

The first rewind continuation reused **97.26%** of its input. Active messages fell from 15 to 3 at navigation. The tangent was absent from active context, the abandoned branch remained stored, the surviving rendered input hashes matched, and the system instructions, tool definitions and cache key were unchanged. The main model recovered the durable token `COBALT-731`.

This establishes immediate prefix reuse for this model/provider/session setup. It does not establish a guaranteed cache TTL, universal hit rate, or a proportional reduction in subscription quota. Pi maps backend `input_tokens_details.cached_tokens` to `usage.cacheRead`; its `usage.input` excludes cached tokens. The report therefore computes total input as `input + cacheRead + cacheWrite`. Dollar amounts in Pi's raw usage are catalog estimates, not subscription charges.

Raw evidence: [requests and usage](results/cache-first/cache.json), [prefix/tree invariants](results/cache-first/cache-invariants.json), [summary](results/cache-first/cache-summary.json).

## 2. Local retention judge

The hand-labeled diagnostic set contains 9 disposable tangents and 17 durable tails. It includes new requirements, useful failed approaches, source text, task corrections, mixed useful/irrelevant content, an adversarial instruction, and useful facts buried in long tails. This is a small diagnostic set, not a representative benchmark or a calibrated safety evaluation.

| Metric | Result |
| --- | ---: |
| Completed judgments | 26/26 |
| Exact four-class agreement | 12/26 (46.15%) |
| Mean local inference time, including first request | 135.9 ms |
| Useful tails discarded at threshold 0.95 | 0/17 |
| Disposable tails collected at threshold 0.95 | 0/9 |
| Useful tails discarded at threshold 0.50 | 1/17 |
| Disposable tails collected at threshold 0.50 | 1/9 |
| Useful tails discarded at threshold 0.70 | 1/17 |
| Disposable tails collected at threshold 0.70 | 0/9 |

The adversarial fixture was the useful tail incorrectly nominated for discard at lower thresholds. Merely lowering the threshold therefore did not produce an acceptable tradeoff. The prompt and fixture labels were not tuned to these outcomes. Shadow mode remains the default; domain-specific training and a separate held-out evaluation would be needed before treating the judge as a dependable collector.

The first attempted GPU run failed because Triton could not find `Python.h`. Installing `python3.12-dev` fixed inference. The failed records remain under `results/judge-base/` for provenance and are excluded from these metrics. Laya also warned that its calibration entry for choices with 11+ options was out of bounds and clamped; these experiments use two and four options, but no task-specific calibration is claimed.

Raw evidence: [all model scores and labels](results/judge-cuda/judge.json), [threshold sweep](results/judge-cuda/judge-summary.json), [checkpoint/runtime metadata](results/judge-cuda/laya-runtime.json).

## 3. Baseline versus automatic GC

Two six-turn sessions received project facts, tangents, a new requirement and a final structured recall query. The automatic session used real local Laya judgments and the 0.95 policy.

| Metric | Baseline | Automatic GC |
| --- | ---: | ---: |
| Required facts recovered | All | All |
| Active messages at completion | 13 | 13 |
| Total input tokens across requests | 1,117 | 1,125 |
| Collected tails | 0 | 0 |

There was **no demonstrated token saving**. The small token difference comes from independently generated replies. These prompts are below the cache experiment's large-prefix regime. This is a fact-retention smoke test, not a coding-quality benchmark.

Raw evidence: [comparison](results/integration-cuda/integration-summary.json), [baseline turns](results/integration-cuda/baseline.json), [GC turns](results/integration-cuda/auto.json), [decision trace](results/integration-cuda/auto-gc.jsonl).

## 4. Tool output filtering and recovery

Two real Pi sessions read the same generated test log, with filtering disabled/enabled. Laya evaluated eight windows and chose `KEEP_FULL`; both runs therefore used 2,531 input tokens and recovered the correct failure. Again, no classifier-driven reduction was observed.

A separate deterministic mechanism check reduced a 36,047-character log to a 222-character excerpt and archive reference while preserving the exact failure line. The original is recoverable byte-for-byte. That check specifies `KEEP_RESULT` explicitly; it is not presented as a successful Laya classification.

Raw evidence: [real tool calls, scores and outputs](results/tools-cuda/tool-filter.json), [externalization mechanism check](results/integration-cuda/externalization.json).

## Implementation verification

`npm run check` and six tests pass. The tests use actual Pi session managers and navigation, with deterministic judge doubles, to isolate checkpoint/persistence/recovery correctness from model quality. They cover unchanged prefix restoration, on-disk reopening of a collected branch, retention of promoted facts, failed inference, shadow behavior, concurrent branch changes, mutation guards and exact artifact recovery.

The implemented foundation is usable for further experiments: reversible tree collection works and cache reuse is measured. The current obstacle to unattended token savings is retention quality, not the Pi/OpenAI transport.

References: [Pi SDK](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md), [Pi extension API](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md), [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), [Laya source and limitations](https://github.com/NandhaKishorM/laya).

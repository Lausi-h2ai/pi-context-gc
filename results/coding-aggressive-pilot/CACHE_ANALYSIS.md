# Why this pilot had no aggressive-arm cache hits

The aggressive arm did not disable prompt caching. Within every trial, the recorded model, instructions, tool definitions and `prompt_cache_key` stayed constant. The Pi tree rewind occurred after the fifth model request; those first five requests already had zero reported cached tokens. Thus rewind cannot explain the initial misses.

The first baseline request after the diagnostic read was about 2,774–2,786 input tokens. The following request and every subsequent request reported 2,560 cached tokens. The aggressive filter reduced the diagnostic output from about 12,300 characters to at most 1,636 characters. Aggressive requests stayed between 547 and 1,866 total input tokens and reported no cache reads.

The [controlled two-request probe](../cache-threshold-probe/summary.json) reused the same instructions and cache key within each session, without tools or rewinds:

| First request input | Second request cached tokens |
| ---: | ---: |
| 1,245 | 0 |
| 1,725 | 0 |
| 2,205 | 1,792 |
| 2,605 | 0 |
| 3,085 | 2,816 |

This supports a length/breakpoint explanation for the coding run, but it does not establish a fixed threshold: the 2,605-token probe missed. OpenAI requires an eligible unchanged prefix and does not guarantee a hit merely because requests share a session. Hidden system tokens do not count toward the documented minimum cacheable prefix, and implicit breakpoint placement matters. The Codex backend did not provide a per-request miss reason in this experiment. See [OpenAI's prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching).

The [earlier long-prefix rewind experiment](../../REPORT.md) recovered a 17,152-token cache hit after Pi navigation. Rewind is compatible with cache reuse when an eligible prefix survives. In this short-task pilot, pruning saved total input tokens but raised uncached input from 24,208 to 31,174. A longer-session benchmark is needed to measure the combined policy when the durable prefix stays comfortably cacheable.

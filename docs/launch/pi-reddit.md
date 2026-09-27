# PiCodingAgent launch draft

Status: prepared, not submitted. This draft was written with AI assistance; the maintainer should review and personalize it. The available tools do not include authenticated Reddit posting. The community's rules page did not expose readable rules during preparation; check the current rules and required flair in the submission UI.

## Title

I built a “forget button” for Pi: 44.6% fewer input tokens in an 8-task pilot, with old tool output recoverable

## Body

Pi reads a huge diagnostic log once. That log can keep traveling through later requests long after the useful part has been found.

I’ve open-sourced **Pi Context GC** to archive eligible old tool output and replace it with a file reference. The agent can read the full output again when it needs the detail. Requirements and source reads stay protected in this benchmark policy.

**Archive the bulk. Keep the evidence.**

[15-second mechanism demo](https://github.com/Lausi-h2ai/pi-context-gc/blob/main/docs/assets/archive-demo.gif) · [Code and quick start](https://github.com/Lausi-h2ai/pi-context-gc)

The latest pilot used eight synthetic Python repair tasks with hidden checks, one trial per arm:

| | Baseline | Laya-guided | Von-guided |
| --- | ---: | ---: | ---: |
| Total input tokens, including cached | 529,263 | 293,319 | 301,038 |
| Input reduction | — | **44.6%** | 43.1% |
| Whole tasks passed | 7/8 | **7/8** | 6/8 |
| Hidden checks passed | 138/147 | 146/147 | 145/147 |

The local judges run on the machine; the coding model in these runs was remote `gpt-6-luna` through Pi’s `openai-codex` provider. The repo includes the traces, judge decisions, evaluator, earlier results, and a no-login demo: `npm ci && npm run demo` after cloning.

The limitations are worth being explicit about. Uncached input **increased 6.4%** with Laya, so this isn’t a demonstrated cost or quota saving. Laya’s savings interval is 17.4–53.9%; the earlier safer policy showed only 7.6% pooled savings. The budget overrides classifier votes, so we still need to show whether the judge earns its complexity compared with a deterministic policy. Equal task-pass counts here don’t establish production accuracy.

Next up: the deterministic control, repeated trials, and unseen tasks. The interactive host currently defaults to conservative shadow mode; the aggressive policy measured here runs through the general benchmark.

If you try it, I’d like to hear which tool outputs keep clogging your sessions and what information your agent needs to retrieve later. If you want to follow the experiments, a GitHub star helps people find the project.

[Full report](https://github.com/Lausi-h2ai/pi-context-gc/blob/main/results/general-v3-aggressive-r1/GENERAL_REPORT.md) · [Results graphic](https://github.com/Lausi-h2ai/pi-context-gc/blob/main/docs/assets/v3-results.png)

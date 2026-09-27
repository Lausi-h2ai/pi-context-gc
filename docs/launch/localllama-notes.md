# LocalLLaMA: source notes for a maintainer-written post

Status: not submitted. These are factual reference notes, not copy to paste as a post.

The [rules available during preparation](https://old.reddit.com/r/LocalLLaMA/about/rules/) prohibit primarily LLM-generated copy/code and bots posing as humans. The stated translation/refinement exception is limited and requires transparent disclosure. They also require affiliation disclosure and limit self-promotion. Do not disguise an AI-written launch draft as a personal post.

The community has a [project showcase thread](https://www.reddit.com/r/LocalLLaMA/comments/1wgcpww/biweekly_megathread_project_showcase/). Its existence does not automatically exempt a project or comment from those rules. Read the current thread and rules before participating. The project's development used AI assistance; be candid about that if discussing the work. The available tools do not include authenticated Reddit posting.

Facts a maintainer can discuss in their own words:

- Own project: MIT-licensed Pi context archiving prototype, with public code, synthetic fixtures, evaluator, full run traces, and negative findings.
- Local component: Laya and Von retention judges ran on an RTX 3070. The benchmark’s coding model was remote `gpt-6-luna`. No local coding-model saving has been measured.
- Mechanism: archive eligible earlier tool output, replace with a file reference, allow later retrieval. Fixed budget can override the local classifier.
- V3 Laya: 529,263 baseline input tokens versus 293,319, including cached input; 44.6% reduction, 7/8 tasks passed in both arms. Hidden checks: 138/147 baseline, 146/147 Laya.
- Uncached input rose 6.4%. This is no demonstrated cost, quota, or latency win. One repetition of eight tasks; paired savings interval 17.4–53.9%.
- Prior safe-policy Laya run saved 7.6% pooled. Every v3 Laya replacement overrode `KEEP_FULL`. Deterministic control and repeated trials are still needed.
- Most relevant local-inference question: does paying for a small local retention model improve selection over deterministic archiving under the same budget? Current data do not answer it.
- The included offline demo checks recovery with a deterministic judge and no model requests. It does not measure inference performance.

Source: https://github.com/Lausi-h2ai/pi-context-gc

Report: https://github.com/Lausi-h2ai/pi-context-gc/blob/main/results/general-v3-aggressive-r1/GENERAL_REPORT.md

"""Summarize observed interventions separately from token differences."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1]).resolve()
summary = json.loads((out / 'summary.json').read_text())
rows = json.loads((out / 'outcomes.json').read_text())
design = json.loads((out / 'design.json').read_text())
# Match runtime.ts hash: SHA256(JSON.stringify(text)), not raw-file SHA256.
checks = {name: hashlib.sha256(json.dumps((root/name).read_text(), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == wanted
          for name, wanted in design['design']['codeHashes'].items()}
if not all(checks.values()):
    raise SystemExit(f'Frozen source hash mismatch: {checks}')
audit = []
for row in rows:
    for event in row.get('filterEvents', []):
        if not event.get('changed'):
            continue
        archive = Path(event['archive'])
        original = archive.read_text()
        retained = None
        for line in Path(row['sessionFile']).read_text().splitlines():
            entry = json.loads(line)
            message = entry.get('message', {})
            if message.get('role') == 'toolResult' and message.get('toolCallId') == event['toolCallId']:
                retained = '\n'.join(c.get('text', '') for c in message.get('content', []) if c.get('type') == 'text')
        action_lines = [line for line in original.splitlines() if line.startswith(('FAILED', 'ERROR', 'WARNING', 'input:', 'expected:', 'actual:'))]
        audit.append({'trial':row['id'], 'archive_hash_matches':hashlib.sha256(original.encode()).hexdigest() == archive.stem,
                      'retained_found':retained is not None, 'actionable_lines_omitted':[line for line in action_lines if retained is not None and line not in retained]})
(out/'retention-audit.json').write_text(json.dumps({'sourceHashesMatch':checks,'changedOutputs':audit}, indent=2)+'\n')
lines = ['# Fixed-policy unseen-task pilot results', '',
         'Three new task domains, five arms, one independent generation per task/arm. Full protocol: `benchmarks/UNSEEN-PILOT.md`. Frozen source hashes verified against pre-run `design.json`.', '',
         '| Arm | Tasks pass | Cases pass | Total input | Cached | Uncached | Output | Input saving | Filters / rewinds | Wall seconds | Judge seconds |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for s in summary:
    lines.append(f"| {s['arm']} | {s['taskPasses']}/{s['trials']} | {s['testsPassed']}/{s['testsTotal']} | {s['inputTotal']:,} | {s['inputCached']:,} | {s['inputUncached']:,} | {s['outputTokens']:,} | {s['inputSavingsPercent']:.2f}% | {s['filteredResults']} / {s['rewinds']} | {s['wallMs']/1000:.1f} | {s['judgeLatencyMs']/1000:.1f} |")
lines += ['', '## Observed result', '',
          'The frozen Laya filter changed zero outputs across all three new tasks, including both Laya-filter arms. Its 1.19% lower token total and better pass count cannot be attributed to filtering. Rewind-only and combined each deleted three unrelated tangents and used about 3% less total input than baseline; this is a small observed difference, not a robust estimate of savings.', '',
          'The deterministic heuristic changed two outputs and reduced total input 30.95%, while cached input fell from 44,032 to 17,920 and uncached input rose from 36,532 to 37,706 (+3.21%). Thus the large total-token reduction is not an uncached-token improvement. JSONL logs were unchanged by both filters.', '',
          'Baseline and heuristic each failed six escaped-record cases (31/37 overall). Both generated a comparison between a single character and a two-backslash string, preventing escape handling. Laya filter-only passed despite no context changes, directly demonstrating generation variability. The heuristic retained every actionable diagnostic line, including the multiline input example; no observed diagnostic loss explains its failure.', '',
          'Recommendation: do not enable the focused classifier filter generally on this evidence. There is no demonstrated filtering advantage over the simple heuristic here. Keep the rewind mechanism experimental; a separately registered long-session test could assess whether its small observed benefit grows under context bloat. Do not retune against these results and call the same tasks unseen again.']
lines += ['', '## Task-level effects', '', '| Task | Arm | Input | Cached | Uncached | Filters | Rewinds | Passed |', '|---|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['task']} | {r['arm']} | {r['inputTotal']:,} | {r['inputCached']:,} | {r['inputUncached']:,} | {r['filteredResults']} | {r['rewinds']} | {r['evaluation']['passed']}/{r['evaluation']['total']} |")
lines += ['', '## Retention audit', '', 'Exact archives and retained tool messages were compared for every changed output. `retention-audit.json` records hashes and missing actionable lines.']
for item in audit:
    lines.append(f"- {item['trial']}: archive hash matches={item['archive_hash_matches']}; retained message found={item['retained_found']}; omitted actionable lines={item['actionable_lines_omitted']}.")
lines += ['', '## Interpretation limits', '', 'Token differences without recorded filtering or rewinds are generation variability, not demonstrated policy savings. All requests, including tool continuations, are counted. Laya runs locally; judge latency is included in wall time but is not provider input. No price conversion is made.', '', 'This is a short six-turn transfer pilot. It does not recreate a long stable cacheable prefix, production tool streams, or sustained context bloat. The JSONL task is a deliberate format outside the unchanged Laya filter gate. Contracts are repeated before implementation, which can mask diagnostic information loss. Hidden cases check return values and exception types but not input mutation. Agent isolation is instruction-level, not a filesystem sandbox. A single trial per cell does not support statistical superiority or a production safety claim.']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(out/'REPORT.md')

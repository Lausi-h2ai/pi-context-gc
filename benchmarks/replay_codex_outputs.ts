/** Offline Laya probe of Codex tool outputs. Never edits or resumes the session. */
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { LayaJudge } from '../src/judge.js';
import { splitOutput } from '../src/aggressive-filter.js';

const [log, destination] = process.argv.slice(2);
if (!log || !destination) throw new Error('Usage: tsx benchmarks/replay_codex_outputs.ts LOG JSON');
const rows = readFileSync(log, 'utf8').trimEnd().split('\n').map(line => JSON.parse(line));
const outputs = rows.filter(row => row.type === 'response_item' && row.payload?.type === 'custom_tool_call_output')
  .map(row => ({ ordinal: row.ordinal, callId: row.payload.call_id,
    text: row.payload.output.filter((x: any) => x.type === 'input_text').map((x: any) => x.text).join('\n') }))
  .filter(row => row.text.length >= 1000);
const judge = new LayaJudge();
const report: any = { source: log, policy: 'exploratory: all Codex tool outputs of at least 1000 characters, split into 1600-character line-preserving chunks',
  objective: 'Evaluate Laya and Pi context-pruning experiments while preserving requirements, code changes, test failures, and evidence.',
  outputs: [] };
try {
  report.laya = await judge.ready;
  for (const [index, output] of outputs.entries()) {
    const chunks = splitOutput(output.text);
    const decisions: any[] = [];
    const kept: string[] = [];
    let omitted = 0;
    for (const chunk of chunks) {
      try {
        const verdict = await judge.judge(`${report.objective} For tool results, retain actionable failures and necessary code or findings; discard routine status lines.`, `Tool exec result chunk:\n${chunk}`);
        decisions.push({ action: verdict.action, discardProbability: verdict.discardProbability,
          durableProbability: verdict.durableProbability, windows: verdict.windows });
        if (verdict.action === 'KEEP_FULL') kept.push(chunk);
        else if (verdict.action === 'KEEP_RESULT') {
          const lines = chunk.split('\n').filter(line => /fail|error|assert|expected|actual|summary|warning/i.test(line));
          if (lines.length) {
            const excerpt = lines.join('\n') + '\n';
            kept.push(excerpt);
            if (excerpt.length < chunk.length) omitted++;
          } else omitted++;
        } else {
          const failures = chunk.split('\n').filter(line => /\b(?:FAILED|ERROR|AssertionError|expected|actual)\b/i.test(line));
          if (failures.length) kept.push(failures.join('\n') + '\n');
          omitted++;
        }
      } catch (error) {
        decisions.push({ error: String(error) }); kept.push(chunk);
      }
    }
    const archive = join('results/codex-session-offline-artifacts', `${createHash('sha256').update(output.text).digest('hex')}.txt`);
    const filtered = `[Full tool result archived at ${archive}; ${omitted} of ${chunks.length} chunks shortened or omitted. Read the archive if exact omitted details are needed.]\n${kept.join('')}`;
    const retainedCharacters = filtered.length < output.text.length ? filtered.length : output.text.length;
    report.outputs.push({ ordinal: output.ordinal, callId: output.callId,
      originalCharacters: output.text.length, retainedCharacters,
      changed: retainedCharacters < output.text.length, decisions });
    if ((index + 1) % 10 === 0) console.error(`Judged ${index + 1}/${outputs.length} outputs`);
  }
} finally {
  judge.close();
  writeFileSync(destination, JSON.stringify(report, null, 2));
}
console.log(JSON.stringify({ judged: report.outputs.length,
  originalCharacters: report.outputs.reduce((n: number, x: any) => n + x.originalCharacters, 0),
  retainedCharacters: report.outputs.reduce((n: number, x: any) => n + x.retainedCharacters, 0),
  changed: report.outputs.filter((x: any) => x.changed).length }));

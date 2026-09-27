/** Offline mechanism demo: real context policy, synthetic log, deterministic judge. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, join, relative } from 'node:path';
import { generalContextPolicy, type ContextPruneEvent } from '../src/general-context-policy.js';

const directory = resolve('.runtime/demo');
mkdirSync(directory, { recursive: true });
const source = Array.from({ length: 160 }, (_, i) => `PASS fixture-${String(i + 1).padStart(3, '0')}: expected value matches actual value`).join('\n')
  + '\nFAIL parse_duration(".5m"): expected 30000, got 0\n';
const events: ContextPruneEvent[] = [];
let handler: (event: any) => Promise<any> = async () => undefined;
generalContextPolicy({
  judge: { judge: async () => ({ action: 'KEEP_FULL', discardProbability: 0,
    durableProbability: 1, windows: 1, latencyMs: 0 }) },
  task: () => 'Repair duration parsing',
  archiveDirectory: join(directory, 'artifacts'),
  retainedFraction: 0.70,
  minimumCharacters: 600,
  protectedReadBasenames: ['requirements.txt', 'solver.py'],
  observe: event => events.push(event),
})({ on: (_name: string, callback: any) => { handler = callback; } } as any);

const messages = [
  { role: 'user', content: 'Inspect the diagnostic log.' },
  { role: 'assistant', content: [{ type: 'toolCall', id: 'log', name: 'read', arguments: { path: 'diagnostic.log' } }] },
  { role: 'toolResult', toolCallId: 'log', toolName: 'read', isError: false, content: [{ type: 'text', text: source }] },
  { role: 'assistant', content: [{ type: 'text', text: 'The duration parser needs a repair.' }] },
  { role: 'user', content: 'Implement the repair.' },
];
const changed = await handler({ type: 'context', messages });
assert.equal(events.length, 1);
const notice = changed.messages[2].content[0].text as string;
const recovered = readFileSync(events[0].archive, 'utf8');
assert.equal(recovered, source);
const hash = (text: string) => createHash('sha256').update(text).digest('hex');
const result = {
  kind: 'Offline mechanism demonstration; synthetic log; deterministic judge; no model requests',
  originalCharacters: source.length,
  replacementCharacters: notice.length,
  archive: relative(process.cwd(), events[0].archive),
  notice,
  judgeAction: events[0].action,
  recoveredFailure: recovered.split('\n').find(line => line.startsWith('FAIL')),
  originalSha256: hash(source),
  recoveredSha256: hash(recovered),
  identical: recovered === source,
};
writeFileSync(join(directory, 'replay.json'), JSON.stringify(result, null, 2) + '\n');
console.log('Pi Context GC — offline mechanism demo\n');
console.log('1. Original tool output:', source.length.toLocaleString(), 'characters');
console.log('2. Later context: archived file reference,', notice.length, 'characters');
console.log('3. Read the archived file:', result.recoveredFailure);
console.log('4. Original and recovered SHA-256:', result.originalSha256);
console.log('   Exact recovery:', result.identical ? 'PASS' : 'FAIL');
console.log('\nThe fixed budget overrides the deterministic KEEP_FULL vote.');
console.log('This demonstrates archive/retrieval mechanics, not classifier quality or token savings.');
console.log('Replay data: .runtime/demo/replay.json');

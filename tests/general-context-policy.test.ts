import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { generalContextPolicy } from '../src/general-context-policy.js';

test('archives an older large tool result and keeps current-turn results exact', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pi-general-context-'));
  try {
    let handler: (event: any) => Promise<any> = async () => undefined;
    let calls = 0;
    const events: any[] = [];
    const factory = generalContextPolicy({
      judge: { judge: async () => { calls++; return { action: 'DISCARD', discardProbability: 0.9,
        durableProbability: 0.1, windows: 1, latencyMs: 1 }; } },
      task: () => 'Fix the parser', archiveDirectory: directory, minimumCharacters: 100,
      retainedFraction: 0.70, observe: event => events.push(event),
    });
    factory({ on: (_event: string, callback: any) => { handler = callback; } } as any);
    const oldText = 'old output\n'.repeat(100);
    const currentText = 'current output\n'.repeat(100);
    const messages = [
      { role: 'user', content: 'investigate' },
      { role: 'toolResult', toolCallId: 'old', toolName: 'read', isError: false,
        content: [{ type: 'text', text: oldText }] },
      { role: 'assistant', content: [{ type: 'text', text: 'I saw the old output' }] },
      { role: 'user', content: 'implement' },
      { role: 'toolResult', toolCallId: 'current', toolName: 'read', isError: false,
        content: [{ type: 'text', text: currentText }] },
    ];
    const first = await handler({ type: 'context', messages });
    assert.equal(first.messages[4].content[0].text, currentText);
    assert.match(first.messages[1].content[0].text, /archived at/);
    assert.equal(readFileSync(events[0].archive, 'utf8'), oldText);
    assert.equal(calls, 1);
    await handler({ type: 'context', messages });
    assert.equal(calls, 1);
    assert.equal(events.length, 1);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test('keeps task contracts exact even when the budget requests pruning', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pi-general-contract-'));
  try {
    let handler: (event: any) => Promise<any> = async () => undefined;
    let calls = 0;
    const factory = generalContextPolicy({
      judge: { judge: async () => { calls++; return { action: 'DISCARD', discardProbability: 0.9,
        durableProbability: 0.1, windows: 1, latencyMs: 1 }; } },
      task: () => 'Implement parser', archiveDirectory: directory,
      minimumCharacters: 100, retainedFraction: 0.50,
    });
    factory({ on: (_event: string, callback: any) => { handler = callback; } } as any);
    const contract = 'A detailed requirement.\n'.repeat(100);
    const messages = [
      { role: 'user', content: 'read requirements' },
      { role: 'assistant', content: [{ type: 'toolCall', id: 'contract-read', name: 'read',
        arguments: { path: 'requirements.txt' } }] },
      { role: 'toolResult', toolCallId: 'contract-read', toolName: 'read', isError: false,
        content: [{ type: 'text', text: contract }] },
      { role: 'user', content: 'implement' },
    ];
    assert.equal(await handler({ type: 'context', messages }), undefined);
    assert.equal(calls, 0);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

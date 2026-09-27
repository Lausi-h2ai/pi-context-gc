import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { PostToolGC } from '../src/post-tool-gc.js';
import { toolFilter, type FilterObservation } from '../src/tool-filter.js';
import { aggressiveToolFilter } from '../src/aggressive-filter.js';
import type { Verdict } from '../src/judge.js';
import type { ContextGC } from '../src/gc.js';

const verdict: Verdict = { action: 'DISCARD', discardProbability: 0.99, durableProbability: 0.01, windows: 1, latencyMs: 1 };
test('post-tool judgment defers navigation and rechecks complete settled tail once', async () => {
  let handler: any;
  let scored = 0, collected = 0;
  const controller = new PostToolGC({ judge: async () => { scored++; return verdict; } }, () => 'Task');
  controller.extension({ on: (_: unknown, h: any) => { handler = h; } } as any);
  await handler({ toolName: 'read', toolCallId: 'one', content: [{ type: 'text', text: 'tangent' }] });
  assert.equal(scored, 1);
  assert.equal(collected, 0);
  const gc = { collect: async () => { collected++; return { action: 'KEEP', reason: 'later state mutation' }; } } as unknown as ContextGC;
  assert.equal((await controller.settle(gc))?.action, 'KEEP');
  assert.equal(collected, 1);
  assert.equal(await controller.settle(gc), undefined);
  assert.equal(collected, 1);
});

test('tool filtering archives before returning excerpt and reports actual size change', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pi-filter-test-'));
  const events: FilterObservation[] = [];
  let handler: any;
  toolFilter({ judge: async () => ({ ...verdict, action: 'KEEP_RESULT' }) }, 'Task', directory, ['read'], e => events.push(e))(
    { on: (_: unknown, h: any) => { handler = h; } } as any);
  const full = 'progress\n'.repeat(1000) + 'FAILED precision: expected 123.00 got 123\n';
  const result = await handler({ toolName: 'read', toolCallId: 'one', content: [{ type: 'text', text: full }] });
  assert.equal(events.length, 1); assert.equal(events[0].changed, true);
  assert.ok(events[0].retainedCharacters < events[0].originalCharacters);
  const archive = result.content[0].text.match(/Full output: (.*?);/)[1];
  assert.equal(readFileSync(archive, 'utf8'), full);
  assert.ok(result.content[0].text.includes('expected 123.00 got 123'));
  assert.equal(await handler({ toolName: 'read', isError: true, content: [{ type: 'text', text: full }] }), undefined);
  assert.equal(await handler({ toolName: 'write', content: [{ type: 'text', text: full }] }), undefined);
  assert.equal(events.length, 1);
});

test('aggressive filtering omits irrelevant chunks while retaining the failing line and exact archive', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pi-aggressive-filter-test-'));
  let handler: any;
  const events: any[] = [];
  aggressiveToolFilter({ judge: async (_task, chunk) => ({ ...verdict,
    action: chunk.includes('FAILED precision') ? 'KEEP_FULL' : 'DISCARD' }) }, () => 'Fix precision', directory,
  ['read'], event => events.push(event))({ on: (_: unknown, h: any) => { handler = h; } } as any);
  const full = 'PASSED unrelated fixture\n'.repeat(250) + 'FAILED precision: expected 123.00 got 123\n';
  const result = await handler({ toolName: 'read', toolCallId: 'one', isError: false, content: [{ type: 'text', text: full }] });
  assert.equal(events[0].changed, true);
  assert.ok(result.content[0].text.length < full.length / 2);
  assert.ok(result.content[0].text.includes('FAILED precision: expected 123.00 got 123'));
  assert.equal(readFileSync(events[0].archive, 'utf8'), full);
  let discardHandler: any;
  aggressiveToolFilter({ judge: async () => verdict }, () => 'Fix precision', directory, ['read'])(
    { on: (_: unknown, h: any) => { discardHandler = h; } } as any);
  const discarded = await discardHandler({ toolName: 'read', toolCallId: 'two', isError: false,
    content: [{ type: 'text', text: full }] });
  assert.ok(discarded.content[0].text.includes('FAILED precision: expected 123.00 got 123'));
});

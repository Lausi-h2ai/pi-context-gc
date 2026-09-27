import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ModelRuntime, SessionManager } from '@earendil-works/pi-coding-agent';
import { choose, ContextGC, externalize, protectedEntries } from '../src/gc.js';
import { makeSession } from '../src/runtime.js';
import type { Verdict } from '../src/judge.js';

const discard: Verdict = { action: 'DISCARD', discardProbability: 0.99, durableProbability: 0.01, windows: 1, latencyMs: 1 };
const usage = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };
function append(session: Awaited<ReturnType<typeof makeSession>>, text: string) {
  session.sessionManager.appendMessage({ role: 'user', content: text, timestamp: Date.now() });
  const id = session.sessionManager.appendMessage({ role: 'assistant', content: [{ type: 'text', text: `Answer: ${text}` }],
    api: 'openai-codex-responses', provider: 'openai-codex', model: 'gpt-6-luna', usage, stopReason: 'stop', timestamp: Date.now() });
  session.refreshContext();
  return id;
}
async function setup() {
  const directory = mkdtempSync(join(tmpdir(), 'pi-gc-test-'));
  const runtime = await ModelRuntime.create({ modelsPath: null, refreshOnCreate: false });
  const session = await makeSession({ runtime, directory });
  return { session, directory, runtime };
}

test('policy fails closed for uncertainty, invalid probabilities and side effects', () => {
  assert.equal(choose(discard, false), 'DROP');
  assert.equal(choose(discard, true), 'KEEP');
  for (const p of [NaN, Infinity, 1.1, 0.7]) assert.equal(choose({ ...discard, discardProbability: p }, false), 'KEEP');
  assert.equal(choose({ ...discard, durableProbability: 0.3 }, false), 'KEEP');
});

test('real Pi navigation removes only tail, preserves prefix, persists branch and restores', async () => {
  const { session, directory, runtime } = await setup();
  try {
    append(session, 'Durable invoice token COBALT.');
    const prefix = JSON.stringify(session.messages);
    const gc = new ContextGC(session, { judge: async () => discard }, 'Invoice parser', join(directory, 'gc.jsonl'), 'auto');
    gc.promote();
    const leaf = append(session, 'Disposable tangent.');
    const decision = await gc.collect();
    assert.equal(decision.action, 'DROP');
    assert.equal(JSON.stringify(session.messages), prefix);
    assert.ok(session.sessionManager.getEntry(leaf));
    assert.ok(readFileSync(decision.archive!, 'utf8').includes('Disposable tangent'));
    const reopened = await makeSession({ runtime, directory, sessionFile: session.sessionFile });
    try {
      assert.equal(JSON.stringify(reopened.messages), prefix);
      const resumedGC = new ContextGC(reopened, { judge: async () => discard }, 'Invoice parser', join(directory, 'gc2.jsonl'), 'auto');
      assert.equal(resumedGC.checkpoint, gc.checkpoint);
    } finally { reopened.dispose(); }
    await gc.restore(leaf);
    assert.ok(JSON.stringify(session.messages).includes('Disposable tangent'));
  } finally { session.dispose(); }
});

test('useful tail promotes checkpoint and later collection cannot delete it', async () => {
  const { session, directory } = await setup();
  try {
    append(session, 'Initial task');
    let verdict = { ...discard, action: 'KEEP_RESULT' as Verdict['action'] };
    const gc = new ContextGC(session, { judge: async () => verdict }, 'Invoice parser', join(directory, 'gc.jsonl'), 'auto');
    append(session, 'New constraint: preserve signs');
    assert.equal((await gc.collect()).action, 'KEEP');
    verdict = discard;
    append(session, 'Tangent');
    await gc.collect();
    assert.ok(JSON.stringify(session.messages).includes('preserve signs'));
    assert.ok(!JSON.stringify(session.messages).includes('Tangent'));
  } finally { session.dispose(); }
});

test('aggressive read-only hint collects a completed result turn but keeps full-retention facts', async () => {
  const { session, directory } = await setup();
  try {
    append(session, 'Initial task');
    let tailVerdict: Verdict = { ...discard, action: 'KEEP_RESULT', discardProbability: 0.25, durableProbability: 0.65 };
    const gc = new ContextGC(session, { judge: async () => tailVerdict }, 'Invoice parser', join(directory, 'aggressive.jsonl'), 'auto', 0.5);
    gc.promote();
    append(session, 'Unrelated aside already answered');
    const toolVote = { ...discard, discardProbability: 0.74, durableProbability: 0.35 };
    assert.equal((await gc.collect(toolVote)).action, 'DROP');
    assert.ok(!JSON.stringify(session.messages).includes('Unrelated aside'));
    tailVerdict = { ...discard, action: 'KEEP_FULL' };
    append(session, 'Useful source fact');
    assert.equal((await gc.collect(toolVote)).action, 'KEEP');
    assert.ok(JSON.stringify(session.messages).includes('Useful source fact'));
  } finally { session.dispose(); }
});

test('inference errors, shadow mode, user targets and branch races retain content', async () => {
  const { session, directory } = await setup();
  try {
    append(session, 'Initial task');
    const failing = new ContextGC(session, { judge: async () => { throw new Error('offline'); } }, 'Task', join(directory, 'failure.jsonl'), 'auto');
    append(session, 'Must remain');
    assert.match((await failing.collect()).reason, /judge failed/);
    const shadow = new ContextGC(session, { judge: async () => discard }, 'Task', join(directory, 'shadow.jsonl'));
    append(session, 'Shadow tangent');
    assert.equal((await shadow.collect()).reason, 'shadow: would discard');
    assert.ok(JSON.stringify(session.messages).includes('Shadow tangent'));
    const racing = new ContextGC(session, { judge: async () => { append(session, 'New concurrent fact'); return discard; } }, 'Task', join(directory, 'race.jsonl'), 'auto');
    append(session, 'Old tangent');
    assert.equal((await racing.collect()).reason, 'session changed during judgment');
    assert.ok(JSON.stringify(session.messages).includes('New concurrent fact'));
    const user = session.sessionManager.getBranch().find(e => e.type === 'message' && e.message.role === 'user')!;
    await assert.rejects(() => racing.restore(user.id), /edit-before/);
  } finally { session.dispose(); }
});

test('mutation calls and compaction protect complete tails even when model votes discard', () => {
  const manager = SessionManager.inMemory();
  manager.appendMessage({ role: 'assistant', content: [{ type: 'toolCall', id: 'call1', name: 'bash', arguments: { command: 'touch changed' } }],
    api: 'openai-codex-responses', provider: 'openai-codex', model: 'gpt-6-luna', usage, stopReason: 'toolUse', timestamp: 0 });
  assert.equal(protectedEntries(manager.getBranch()), true);
  const other = SessionManager.inMemory();
  other.appendCompaction('summary', null, 100);
  assert.equal(protectedEntries(other.getBranch()), true);
});

test('externalized output is byte-for-byte recoverable and excerpt retains failure', () => {
  const dir = mkdtempSync(join(tmpdir(), 'pi-artifact-test-'));
  const text = 'noise\n'.repeat(3000) + 'FAILED expected 123.00 got 123\n';
  const result = externalize(text, dir, 'KEEP_RESULT');
  const path = result.match(/Full output: (.*?);/)![1];
  assert.equal(readFileSync(path, 'utf8'), text);
  assert.ok(result.includes('FAILED expected 123.00 got 123'));
  assert.ok(result.length < text.length / 10);
});

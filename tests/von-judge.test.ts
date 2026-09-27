import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { VonJudge } from '../src/von-judge.js';

function worker(contents: string): { directory: string; path: string } {
  const directory = mkdtempSync(join(tmpdir(), 'pi-von-protocol-'));
  const path = join(directory, 'worker.mjs');
  writeFileSync(path, contents);
  return { directory, path };
}

test('VonJudge starts a local worker and validates a retention verdict', async () => {
  const fake = worker(`
    process.stdout.write(JSON.stringify({ready:true, model:'von-1.2.0', revision:'test'}) + '\\n');
    let pending = '';
    process.stdin.on('data', chunk => {
      pending += chunk;
      for (const line of pending.split('\\n').slice(0, -1)) {
        const request = JSON.parse(line);
        process.stdout.write(JSON.stringify({id:request.id, action:'DISCARD', discardProbability:0.98, durableProbability:0.02, windows:1, latencyMs:1, raw:{test:true}}) + '\\n');
      }
      pending = pending.slice(pending.lastIndexOf('\\n') + 1);
    });
  `);
  const judge = new VonJudge({
    python: process.execPath,
    worker: fake.path,
    cwd: fake.directory,
    inheritStderr: false,
    startupTimeoutMs: 2_000,
    inferenceTimeoutMs: 2_000,
  });
  try {
    assert.equal((await judge.ready).model, 'von-1.2.0');
    const verdict = await judge.judge('Fix the parser', 'unrelated aside');
    assert.deepEqual(verdict, {
      action: 'DISCARD',
      discardProbability: 0.98,
      durableProbability: 0.02,
      windows: 1,
      latencyMs: 1,
      raw: { test: true },
    });
  } finally {
    judge.close();
  }
});

test('VonJudge rejects startup failure so callers can retain content', async () => {
  const fake = worker("process.stdout.write(JSON.stringify({error:'von-sdk is unavailable'}) + '\\n'); process.exit(17);");
  const judge = new VonJudge({
    python: process.execPath,
    worker: fake.path,
    cwd: fake.directory,
    inheritStderr: false,
    startupTimeoutMs: 2_000,
  });
  await assert.rejects(judge.ready, /Von startup failed: von-sdk is unavailable/);
  judge.close();
});

test('VonJudge rejects malformed verdicts instead of making a retention decision', async () => {
  const fake = worker(`
    process.stdout.write(JSON.stringify({ready:true}) + '\\n');
    process.stdin.on('data', chunk => {
      const request = JSON.parse(String(chunk));
      process.stdout.write(JSON.stringify({id:request.id, action:'DISCARD', discardProbability:4, durableProbability:0, windows:1, latencyMs:1}) + '\\n');
    });
  `);
  const judge = new VonJudge({
    python: process.execPath,
    worker: fake.path,
    cwd: fake.directory,
    inheritStderr: false,
    startupTimeoutMs: 2_000,
    inferenceTimeoutMs: 2_000,
  });
  try {
    await judge.ready;
    await assert.rejects(judge.judge('Task', 'tail'), /invalid discardProbability/);
  } finally {
    judge.close();
  }
});

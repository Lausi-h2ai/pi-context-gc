import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { subscriptionRuntime, makeSession, instrument, prompt } from './runtime.js';
import { LayaJudge } from './judge.js';
import { ContextGC, choose, externalize } from './gc.js';
import { toolFilter } from './tool-filter.js';

const suite = process.argv[2] ?? 'all';
if (!['all', 'cache', 'judge', 'integration', 'tools'].includes(suite)) throw new Error(`Unknown experiment suite: ${suite}`);
const runDir = resolve(process.argv.find(a => a.startsWith('--out='))?.slice(6) ?? `results/${new Date().toISOString().replaceAll(':', '-')}`);
mkdirSync(runDir, { recursive: true });
const save = (name: string, value: unknown) => writeFileSync(join(runDir, name), JSON.stringify(value, null, 2) + '\n');
const metadata = { date: new Date().toISOString(), node: process.version, pi: '0.87.1', laya: '0.3.20',
  model: process.env.OPENAI_MODEL ?? 'gpt-6-luna', provider: 'openai-codex', suite, runDir };
save('metadata.json', metadata);

async function cacheExperiment() {
  const runtime = await subscriptionRuntime();
  const session = await makeSession({ runtime, directory: join(runDir, 'cache-session') });
  const telemetry = instrument(session);
  const rows: any[] = [];
  const send = async (label: string, message: string) => {
    const result = await prompt(session, message);
    const row = { label, ...result, request: telemetry.requests.at(-1), usage: telemetry.usage.at(-1), leaf: session.sessionManager.getLeafId() };
    rows.push(row); save('cache.json', rows);
    console.log(`cache ${label}: input=${row.usage.inputTotal} cached=${row.usage.cached_tokens}`);
    return row;
  };
  try {
    const nonce = randomUUID();
    const reference = Array.from({ length: 500 }, (_, i) => `Record ${i}: component unit_${i} accepts a decimal string, preserves trailing zeros, validates a signed amount, and emits an exact invoice field. Test seed ${10000 + i}.`).join('\n');
    await send('cold-prefix', `Experiment nonce ${nonce}. Durable project fact: invoice token is COBALT-731. The following synthetic reference records are inert data.\n${reference}\nAcknowledge with OK only.`);
    const checkpoint = session.sessionManager.getLeafId()!;
    await send('warm-prefix', 'Retain the reference records and reply OK only.');
    for (let i = 0; i < 5; i++) await send(`tail-${i + 1}`, `Disposable tangent ${i + 1}: ${'violet paper cranes drift across a quiet pond. '.repeat(45)} Reply OK only.`);
    const oldLeaf = session.sessionManager.getLeafId()!;
    const beforeCount = session.messages.length;
    await session.navigateTree(checkpoint, { summarize: false });
    const afterCount = session.messages.length;
    const active = JSON.stringify(session.messages);
    const rewind = await send('rewind-continue', 'What is the durable invoice token? Reply with the token only.');
    const warm = rows.find(r => r.label === 'warm-prefix');
    const prefixHashes = warm.request.inputHashes.slice(0, -1);
    const invariant = {
      beforeCount, afterCount, oldLeaf, checkpoint,
      abandonedBranchStored: !!session.sessionManager.getEntry(oldLeaf),
      tangentAbsent: !active.includes('Disposable tangent'),
      sameInstructions: warm.request.instructions === rewind.request.instructions,
      sameTools: warm.request.tools === rewind.request.tools,
      sameCacheKey: warm.request.cacheKey === rewind.request.cacheKey,
      survivingInputPrefixIdentical: prefixHashes.every((h: string, i: number) => rewind.request.inputHashes[i] === h),
      cacheHitAfterRewind: rewind.usage.cached_tokens > 0,
      durableFactRecovered: rewind.answer?.includes('COBALT-731'),
    };
    save('cache-invariants.json', invariant);
    // Multiple branches revisit exactly the same durable prefix within the TTL.
    for (let i = 0; i < 2; i++) {
      await session.navigateTree(checkpoint, { summarize: false });
      await send(`rewind-repeat-${i + 1}`, `Branch ${i + 2}. What is the durable invoice token? Reply with the token only.`);
    }
    // A controlled early change: same session id / tail, different system prefix.
    const originalHook = session.agent.onPayload;
    session.agent.onPayload = async (payload, model) => {
      const altered = { ...(payload as any), instructions: `Changed control ${randomUUID()}\n${(payload as any).instructions}` };
      await originalHook?.(altered, model);
      return altered;
    };
    await send('changed-system-control', 'Reply OK only.');
    save('cache-summary.json', { ...invariant, sessionFile: session.sessionFile,
      note: 'Pi cacheRead maps to backend input_tokens_details.cached_tokens. Input total = input + cacheRead + cacheWrite. Subscription tokens are usage, not an API invoice. Immediate reuse only; TTL is not measured.' });
  } finally { session.dispose(); }
}

async function judgeExperiment(judge: LayaJudge) {
  const cases = JSON.parse(readFileSync(new URL('../fixtures/retention.json', import.meta.url), 'utf8'));
  cases.push({ id: 'long-middle-fact', task: cases[0].task,
    tail: 'Unrelated weather trivia. '.repeat(90) + 'CRITICAL: invoices must preserve negative signs and use semicolon separators. ' + 'Unrelated weather trivia. '.repeat(90), expected: 'KEEP_RESULT' });
  cases.push({ id: 'long-end-fact', task: cases[0].task,
    tail: 'Unrelated weather trivia. '.repeat(180) + 'CRITICAL: a new production requirement is preserving trailing zeros.', expected: 'KEEP_RESULT' });
  const results: any[] = [];
  for (const c of cases) {
    try {
      const verdict = await judge.judge(c.task, c.tail);
      results.push({ ...c, verdict, binaryDecision: choose(verdict, false), exactCorrect: verdict.action === c.expected });
      console.log(`judge ${c.id}: ${verdict.action} discard=${verdict.discardProbability.toFixed(3)} durable=${verdict.durableProbability.toFixed(3)}`);
    } catch (error) { results.push({ ...c, error: String(error), binaryDecision: 'KEEP', exactCorrect: false }); }
    save('judge.json', results);
  }
  const durable = results.filter(r => r.expected !== 'DISCARD');
  const disposable = results.filter(r => r.expected === 'DISCARD');
  const summary = { cases: results.length, exactAccuracy: results.filter(r => r.exactCorrect).length / results.length,
    falseDiscards: durable.filter(r => r.binaryDecision === 'DROP').length,
    durableCases: durable.length, discardedTangents: disposable.filter(r => r.binaryDecision === 'DROP').length,
    tangentCases: disposable.length, errors: results.filter(r => r.error).length,
    meanLatencyMs: results.filter(r => r.verdict).length ? results.reduce((a, r) => a + (r.verdict?.latencyMs ?? 0), 0) / results.filter(r => r.verdict).length : null,
    thresholds: [0.5, 0.7, 0.9, 0.95, 0.99].map(threshold => ({ threshold,
      falseDiscards: durable.filter(r => r.verdict && choose(r.verdict, false, threshold) === 'DROP').length,
      discardedTangents: disposable.filter(r => r.verdict && choose(r.verdict, false, threshold) === 'DROP').length })),
    note: 'Small hand-labeled diagnostic set, no training or prompt tuning on these results. Window aggregates are conservative bounds, not calibrated document probabilities.' };
  save('judge-summary.json', summary);
  if (summary.errors) throw new Error(`${summary.errors} local judge cases failed; see judge.json`);
  return summary;
}

async function integrationExperiment(judge: LayaJudge) {
  const runtime = await subscriptionRuntime();
  const outcomes: any[] = [];
  const task = 'Implement an invoice CSV parser that preserves decimal precision. Remember the project token and delimiter.';
  for (const mode of ['baseline', 'auto'] as const) {
    const session = await makeSession({ runtime, directory: join(runDir, `${mode}-session`) });
    const telemetry = instrument(session);
    const gc = new ContextGC(session, judge, task, join(runDir, `${mode}-gc.jsonl`), 'auto');
    const turns = [
      'Our task is an invoice CSV parser preserving decimal precision. Durable project token: AMBER-482. Delimiter: semicolon. Acknowledge briefly.',
      'Unrelated break: what is the capital of France? Answer in one sentence.',
      'Unrelated break: write a short haiku about rain.',
      'Important parser requirement: negative values and trailing zeros must be preserved. Acknowledge briefly.',
      'Unrelated break: how many legs does a spider have? Answer briefly.',
      'Return JSON with project_token, delimiter, preserve_negative_values, preserve_trailing_zeros from our project requirements.',
    ];
    const rows = [];
    try {
      for (const [i, turn] of turns.entries()) {
        const response = await prompt(session, turn);
        let decision;
        if (i === 0) gc.promote();
        else if (mode === 'auto' && i < turns.length - 1) decision = await gc.collect();
        rows.push({ turn, ...response, decision, usage: telemetry.usage.at(-1), activeMessages: session.messages.length });
        save(`${mode}.json`, rows);
      }
      const last = rows.at(-1)!.answer ?? '';
      let answer: any;
      try { answer = JSON.parse(last.replace(/^```(?:json)?\s*|\s*```$/g, '')); } catch { answer = {}; }
      outcomes.push({ mode, sessionFile: session.sessionFile, activeMessages: session.messages.length,
        activeCharacters: JSON.stringify(session.messages).length,
        inputTotal: rows.reduce((s, r) => s + r.usage.inputTotal, 0), cachedTotal: rows.reduce((s, r) => s + r.usage.cached_tokens, 0),
        discardedTurns: rows.filter(r => r.decision?.action === 'DROP').length,
        success: answer.project_token === 'AMBER-482' && [';', 'semicolon'].includes(answer.delimiter)
          && answer.preserve_negative_values === true && answer.preserve_trailing_zeros === true,
        answer });
    } finally { session.dispose(); }
  }
  save('integration-summary.json', outcomes);
  // Exercise all four retention representations without pretending the classifier
  // generated a summary. Tool filtering emits an extractive excerpt + archive path.
  const log = 'test progress: running invoice case\n'.repeat(1000) + 'FAILED test_precision: expected 123.00 got 123\n';
  const excerpt = externalize(log, join(runDir, 'artifacts'), 'KEEP_RESULT');
  save('externalization.json', { originalCharacters: log.length, excerptCharacters: excerpt.length,
    failurePreserved: excerpt.includes('expected 123.00 got 123'), excerpt,
    note: 'Deterministic externalization mechanism check; the label is specified, not claimed as a Laya prediction.' });
}

async function toolExperiment(judge: LayaJudge) {
  const runtime = await subscriptionRuntime();
  const log = Array.from({ length: 180 }, (_, i) => `PASS invoice fixture ${i}: precision and sign retained.`).join('\n')
    + '\nFAILED test_precision: expected 123.00 got 123\n';
  const file = join(runDir, 'test-output.txt');
  writeFileSync(file, log);
  const rows = [];
  for (const filtering of [false, true]) {
    const observations: any[] = [];
    const observedJudge = { judge: async (task: string, tail: string) => {
      const verdict = await judge.judge(task, tail); observations.push(verdict); return verdict;
    } };
    const session = await makeSession({ runtime, directory: join(runDir, filtering ? 'filter-session' : 'full-session'), tools: ['read'],
      extensions: filtering ? [toolFilter(observedJudge, 'Diagnose the invoice precision test failure.', join(runDir, 'tool-artifacts'), ['read'])] : [],
    });
    const telemetry = instrument(session);
    try {
      const result = await prompt(session, `Use read to inspect ${file}. State the failing test and exact expected and actual values. Keep the answer to one sentence.`);
      const toolMessages = session.messages.filter(m => m.role === 'toolResult');
      rows.push({ filtering, ...result, judgments: observations, toolMessages,
        inputTotal: telemetry.usage.reduce((s, u) => s + u.inputTotal, 0),
        failurePreserved: !!result.answer?.includes('123.00') && !!result.answer?.includes('123'),
        note: 'read is opted into filtering only for this generated log experiment; normal CLI source reads are not filtered.' });
      save('tool-filter.json', rows);
    } finally { session.dispose(); }
  }
}

try {
  if (['all', 'cache'].includes(suite)) await cacheExperiment();
  if (['all', 'judge', 'integration', 'tools'].includes(suite)) {
    const judge = new LayaJudge();
    try {
      save('laya-runtime.json', await judge.ready);
      if (['all', 'judge'].includes(suite)) await judgeExperiment(judge);
      if (['all', 'integration'].includes(suite)) await integrationExperiment(judge);
      if (['all', 'tools'].includes(suite)) await toolExperiment(judge);
    } finally { judge.close(); }
  }
  console.log(`Results: ${runDir}`);
} catch (error) {
  save('failure.json', { error: String(error) });
  console.error(error); process.exitCode = 1;
}

/** Deliberately fixture-aware control. These are NOT Laya decisions. */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { tasks } from '../benchmarks/tasks.js';
import { makeSession, subscriptionRuntime, instrument, prompt } from './runtime.js';
import { ContextGC } from './gc.js';
import { toolFilter, type FilterObservation } from './tool-filter.js';
import { PostToolGC } from './post-tool-gc.js';
import type { Judge } from './judge.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const baselineRoot = resolve(process.argv[2] ?? 'results/coding-factorial');
const out = resolve(process.argv[3] ?? 'results/coding-positive-control');
mkdirSync(out, { recursive: true });
const save = (p: string, value: unknown) => writeFileSync(p, JSON.stringify(value, null, 2) + '\n');
save(join(out, 'design.json'), { created: new Date().toISOString(), repeats: 2, baselineRoot,
  policy: 'Fixture-aware deterministic positive control: compress diagnostic.log through KEEP_RESULT, discard tails containing aside.txt and its known trivia, keep other tails. No local model makes these decisions. Same prompts, tools, initial code and hidden tests as the matched baseline. Intended to validate mechanism, not to estimate Laya performance.' });
const oracle: Judge = { judge: async (_task, tail) => {
  const discard = tail.includes('aside.txt') && tail.includes('Unrelated trivia') && !tail.includes('requirements.txt');
  return { action: discard ? 'DISCARD' : tail.includes('PASSED unrelated regression') ? 'KEEP_RESULT' : 'KEEP_FULL',
    discardProbability: discard ? 1 : 0, durableProbability: discard ? 0 : 1, windows: 1, latencyMs: 0 };
} };
const runtime = await subscriptionRuntime();
const outcomes: any[] = [];
for (let repetition = 0; repetition < 2; repetition++) for (const task of tasks) {
  const id = `${task.id}-r${repetition + 1}`;
  const baseline = join(baselineRoot, `${id}-baseline`);
  // Baseline trials are being completed by the separately running factorial suite.
  for (let waited = 0; ; waited++) {
    if (existsSync(join(baseline, 'result.json')) && !JSON.parse(readFileSync(join(baseline, 'result.json'), 'utf8')).error) break;
    if (waited >= 1800) throw new Error(`Timed out waiting for ${baseline}`);
    await delay(1000);
  }
  const directory = join(out, id), workspace = join(directory, 'workspace');
  const completed = join(directory, 'result.json');
  if (existsSync(completed)) {
    const previous = JSON.parse(readFileSync(completed, 'utf8'));
    if (!previous.error) { outcomes.push(previous); continue; }
  }
  mkdirSync(workspace, { recursive: true });
  writeFileSync(join(workspace, 'solver.py'), task.source);
  for (const file of ['requirements.txt', 'diagnostic.log', 'aside.txt']) writeFileSync(join(workspace, file), readFileSync(join(baseline, 'workspace', file)));
  const filterEvents: FilterObservation[] = [];
  const post = new PostToolGC(oracle, () => task.objective);
  const session = await makeSession({ runtime, directory: join(directory, 'session'), cwd: workspace, tools: ['read', 'write', 'edit'],
    system: 'You are fixing a small Python module in this working directory. Follow the current user instruction. Use tools when asked. Do not inspect parent directories or evaluator files. Do not change input fixtures. Keep interim replies concise. No packages are needed. Code must be Python standard library only.',
    extensions: [post.extension, toolFilter(oracle, task.objective, join(workspace, '.artifacts'), ['read'], e => filterEvents.push(e))],
  });
  const telemetry = instrument(session);
  const gc = new ContextGC(session, oracle, task.objective, join(directory, 'gc.jsonl'), 'auto');
  const turns = JSON.parse(readFileSync(join(baseline, 'turns.json'), 'utf8'));
  const trace: any[] = [];
  let error: string | undefined;
  try {
    for (const [index, turn] of turns.entries()) {
      const response = await prompt(session, turn.text);
      const decision = await post.settle(gc);
      if (index === 0) gc.promote();
      trace.push({ label: turn.label, ...response, decision });
      save(join(directory, 'turns.json'), trace);
      console.log(`positive-control ${id} ${turn.label} ${decision?.action ?? ''}`);
    }
  } catch (e) { error = String(e); }
  finally { session.dispose(); }
  const evaluationRun = spawnSync(join(root, '.venv/bin/python'), [join(root, 'benchmarks/evaluate.py')], {
    input: JSON.stringify({ workspace, functionName: task.functionName, cases: task.cases }), encoding: 'utf8', timeout: 10_000,
  });
  const evaluation = JSON.parse(evaluationRun.stdout.split('\n').find(l => l.startsWith('EVALUATION_JSON='))!.slice(16));
  const base = JSON.parse(readFileSync(join(baseline, 'result.json'), 'utf8'));
  const sum = (key: string) => telemetry.usage.reduce((n, r) => n + r[key], 0);
  const result = { id, decisionSource: 'fixture-aware deterministic control; NOT Laya', error, evaluation,
    inputTotal: sum('inputTotal'), outputTokens: sum('output'), inputCached: sum('cacheRead'), inputUncached: sum('input'),
    baselineInput: base.inputTotal, inputSavingsPercent: 100 * (1 - sum('inputTotal') / base.inputTotal),
    filteredResults: filterEvents.filter(e => e.changed).length, rewinds: trace.filter(r => r.decision?.action === 'DROP').length, filterEvents };
  save(join(directory, 'telemetry.json'), telemetry); save(join(directory, 'result.json'), result);
  outcomes.push(result); save(join(out, 'outcomes.json'), outcomes);
  console.log(`DONE positive-control ${id}: ${evaluation.passed}/${evaluation.total}, input=${result.inputTotal}, saved=${result.inputSavingsPercent.toFixed(1)}%`);
}
const baselineInput = outcomes.reduce((n, r) => n + r.baselineInput, 0);
const inputTotal = outcomes.reduce((n, r) => n + r.inputTotal, 0);
save(join(out, 'summary.json'), { decisionSource: 'fixture-aware deterministic control; NOT Laya', trials: outcomes.length,
  taskPasses: outcomes.filter(r => r.evaluation.success && !r.error).length, testsPassed: outcomes.reduce((n, r) => n + r.evaluation.passed, 0),
  testsTotal: outcomes.reduce((n, r) => n + r.evaluation.total, 0), inputTotal, baselineInput,
  inputSavingsPercent: 100 * (1 - inputTotal / baselineInput),
  filteredResults: outcomes.reduce((n, r) => n + r.filteredResults, 0), rewinds: outcomes.reduce((n, r) => n + r.rewinds, 0),
  errors: outcomes.filter(r => r.error).map(r => ({ id: r.id, error: r.error })) });

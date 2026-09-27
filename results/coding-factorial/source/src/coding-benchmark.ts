import { mkdirSync, readFileSync, writeFileSync, appendFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tasks, type CodingTask } from '../benchmarks/tasks.js';
import { LayaJudge, type Judge } from './judge.js';
import { ContextGC } from './gc.js';
import { toolFilter, type FilterObservation } from './tool-filter.js';
import { PostToolGC, type PostToolObservation } from './post-tool-gc.js';
import { subscriptionRuntime, makeSession, instrument, prompt, hash } from './runtime.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = resolve(process.argv.find(a => a.startsWith('--out='))?.slice(6) ?? `results/coding-${new Date().toISOString().replaceAll(':', '-')}`);
const repeats = Number(process.argv.find(a => a.startsWith('--repeats='))?.slice(10) ?? 2);
if (!Number.isInteger(repeats) || repeats < 1 || repeats > 10) throw new Error('repeats must be 1..10');
const arms = [
  { name: 'baseline', filter: false, rewind: false, threshold: 0.95 },
  { name: 'filter', filter: true, rewind: false, threshold: 0.95 },
  { name: 'rewind', filter: false, rewind: true, threshold: 0.95 },
  { name: 'both', filter: true, rewind: true, threshold: 0.95 },
  { name: 'both-exploratory', filter: true, rewind: true, threshold: 0.50 },
];
const save = (path: string, value: unknown) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n');
mkdirSync(out, { recursive: true });
const codeHashes = Object.fromEntries(['src/coding-benchmark.ts', 'src/gc.ts', 'src/tool-filter.ts', 'src/post-tool-gc.ts', 'src/runtime.ts', 'python/judge.py', 'benchmarks/tasks.ts', 'benchmarks/evaluate.py'].map(p => [p, hash(readFileSync(join(root, p), 'utf8'))]));
const design = { repeats, arms, tasks: tasks.map(t => ({ id: t.id, tests: t.cases.length, hash: hash(t) })),
  codeHashes, model: process.env.OPENAI_MODEL ?? 'gpt-6-luna',
  primaryMetrics: ['total input tokens across every model call', 'all hidden tests pass'],
  secondaryMetrics: ['uncached input', 'cached input', 'output tokens', 'test-case accuracy', 'latency', 'actual filtered results', 'actual rewinds'],
  method: 'Fresh isolated workspaces. Task/repetition-matched conditions with rotating arm order. Unmodified model weights and classifier prompts. Independent model generations. No repair after hidden tests. Exploratory threshold is reported separately. Post-tool scores happen synchronously; full-tail rewind checks happen only at a settled boundary.',
};
const manifest = join(out, 'design.json');
if (existsSync(manifest)) {
  if (hash(JSON.parse(readFileSync(manifest, 'utf8')).design) !== hash(design)) throw new Error('Design changed; use a fresh output directory');
} else save(manifest, { created: new Date().toISOString(), design });

function evaluate(task: CodingTask, workspace: string) {
  const p = spawnSync(join(root, '.venv/bin/python'), [join(root, 'benchmarks/evaluate.py')], {
    input: JSON.stringify({ workspace, functionName: task.functionName, cases: task.cases }),
    encoding: 'utf8', timeout: 10_000, cwd: workspace, maxBuffer: 1024 * 1024,
  });
  const line = p.stdout?.split('\n').find(l => l.startsWith('EVALUATION_JSON='));
  return line ? JSON.parse(line.slice('EVALUATION_JSON='.length)) : { passed: 0, total: task.cases.length, success: false, error: String(p.error ?? p.stderr) };
}

const outcomes: any[] = [];
const judge = new LayaJudge();
try {
  save(join(out, 'laya-runtime.json'), await judge.ready);
  const runtime = await subscriptionRuntime();
  for (let repetition = 0; repetition < repeats; repetition++) for (const [taskIndex, task] of tasks.entries()) {
    const offset = (repetition + taskIndex) % arms.length;
    const order = [...arms.slice(offset), ...arms.slice(0, offset)];
    for (const arm of order) {
      const id = `${task.id}-r${repetition + 1}-${arm.name}`;
      const directory = join(out, id);
      const resultFile = join(directory, 'result.json');
      if (existsSync(resultFile)) { outcomes.push(JSON.parse(readFileSync(resultFile, 'utf8'))); continue; }
      const workspace = join(directory, 'workspace');
      mkdirSync(workspace, { recursive: true });
      writeFileSync(join(workspace, 'solver.py'), task.source);
      writeFileSync(join(workspace, 'requirements.txt'), task.requirements);
      const diagnostic = Array.from({ length: 125 }, (_, i) => `PASSED unrelated regression group ${i}: fixture processed successfully; no new actionable findings.`).join('\n')
        + `\nFAILED target behavior: ${task.id === 'invoice' ? 'expected amount 123.00 but got 123.0' : task.id === 'retry' ? 'expected zero retries after HTTP 401, got one retry' : 'expected ValueError for ../secret, got secret'}.\n`;
      writeFileSync(join(workspace, 'diagnostic.log'), diagnostic);
      writeFileSync(join(workspace, 'aside.txt'), 'Unrelated trivia for a short break: Paris is the capital of France. Spiders have eight legs. This document has no software requirements.\n');
      const initialEvaluation = evaluate(task, workspace);
      if (initialEvaluation.success) throw new Error(`Invalid benchmark: initial ${task.id} already passes`);
      const filterEvents: FilterObservation[] = [];
      const postToolEvents: PostToolObservation[] = [];
      let judgeCalls = 0, judgeLatencyMs = 0;
      const counted: Judge = { judge: async (objective, tail) => {
        judgeCalls++;
        const result = await judge.judge(objective, tail); judgeLatencyMs += result.latencyMs;
        appendFileSync(join(directory, 'judge.jsonl'), JSON.stringify({ inputHash: hash({ objective, tail }), inputCharacters: tail.length, result }) + '\n');
        return result;
      } };
      const post = new PostToolGC(counted, () => task.objective, event => postToolEvents.push(event));
      const session = await makeSession({ runtime, directory: join(directory, 'session'), cwd: workspace,
        tools: ['read', 'write', 'edit'],
        system: 'You are fixing a small Python module in this working directory. Follow the current user instruction. Use tools when asked. Do not inspect parent directories or evaluator files. Do not change input fixtures. Keep interim replies concise. No packages are needed. Code must be Python standard library only.',
        extensions: [
          ...(arm.rewind ? [post.extension] : []),
          ...(arm.filter ? [toolFilter(counted, task.objective, join(workspace, '.artifacts'), ['read'], event => filterEvents.push(event))] : []),
        ],
      });
      const telemetry = instrument(session);
      const gc = new ContextGC(session, counted, task.objective, join(directory, 'gc.jsonl'), 'auto', arm.threshold);
      const turns = [
        { label: 'bootstrap', text: task.initial + ' Do not inspect files or implement yet. Acknowledge in one sentence.' },
        { label: 'diagnostic', text: 'Read diagnostic.log completely using read. Identify the actionable failure in one sentence. Do not implement yet.' },
        { label: 'tangent', text: 'As an unrelated short break, read aside.txt and answer: what is the capital mentioned? Do not change anything.' },
        { label: 'constraints', text: 'Back to the task: read requirements.txt completely and note all requirements for the implementation. Do not implement yet; acknowledge in one sentence.' },
        { label: 'implement', text: 'Now fix solver.py using the requirements and findings gathered above. Inspect its current contents, then implement the complete solution. Do not change any fixture files. When finished, give one sentence summarizing the change.' },
      ];
      const trace: any[] = [];
      const start = performance.now();
      let error: string | undefined;
      try {
        for (const [turnIndex, turn] of turns.entries()) {
          const timer = setTimeout(() => { void session.abort(); }, 120_000);
          try {
            const response = await prompt(session, turn.text);
            const decision = arm.rewind ? await post.settle(gc) : undefined;
            if (turnIndex === 0) gc.promote();
            trace.push({ ...turn, ...response, decision, messages: session.messages.length });
            save(join(directory, 'turns.json'), trace);
            console.log(`${id} ${turn.label}${decision ? ` GC=${decision.action} (${decision.reason})` : ''}`);
          } finally { clearTimeout(timer); }
        }
      } catch (e) { error = String(e); }
      const evaluation = evaluate(task, workspace);
      const sum = (key: string) => telemetry.usage.reduce((total, row) => total + (row[key] ?? 0), 0);
      const result = {
        id, task: task.id, repetition, arm: arm.name, config: arm, error, initialEvaluation, evaluation,
        inputTotal: sum('inputTotal'), inputUncached: sum('input'), inputCached: sum('cacheRead'), outputTokens: sum('output'),
        allTokens: sum('inputTotal') + sum('output'), requests: telemetry.requests.length,
        wallMs: performance.now() - start, judgeCalls, judgeLatencyMs,
        filteredResults: filterEvents.filter(e => e.changed).length,
        removedToolCharacters: filterEvents.reduce((n, e) => n + e.originalCharacters - e.retainedCharacters, 0),
        rewinds: trace.filter(t => t.decision?.action === 'DROP').length,
        finalMessages: session.messages.length, finalSourceHash: hash(readFileSync(join(workspace, 'solver.py'), 'utf8')),
        sessionFile: session.sessionFile, filterEvents, postToolEvents,
      };
      save(join(directory, 'telemetry.json'), telemetry);
      save(resultFile, result);
      outcomes.push(result); save(join(out, 'outcomes.json'), outcomes);
      session.dispose();
      console.log(`DONE ${id}: ${evaluation.passed}/${evaluation.total} tests, input=${result.inputTotal}, filtered=${result.filteredResults}, rewinds=${result.rewinds}`);
    }
  }
  const summary = arms.map(arm => {
    const rows = outcomes.filter(r => r.arm === arm.name);
    const sum = (key: string) => rows.reduce((n, r) => n + (r[key] ?? 0), 0);
    const paired = rows.map(row => {
      const baseline = outcomes.find(r => r.task === row.task && r.repetition === row.repetition && r.arm === 'baseline');
      return { id: row.id, baselineInput: baseline.inputTotal, input: row.inputTotal,
        savedInput: baseline.inputTotal - row.inputTotal, savedPercent: 100 * (1 - row.inputTotal / baseline.inputTotal),
        baselineSuccess: baseline.evaluation.success, success: row.evaluation.success };
    });
    const baselineInput = paired.reduce((n, r) => n + r.baselineInput, 0);
    return { arm: arm.name, trials: rows.length, taskPasses: rows.filter(r => r.evaluation.success && !r.error).length,
      testsPassed: rows.reduce((n, r) => n + r.evaluation.passed, 0), testsTotal: rows.reduce((n, r) => n + r.evaluation.total, 0),
      inputTotal: sum('inputTotal'), inputUncached: sum('inputUncached'), inputCached: sum('inputCached'), outputTokens: sum('outputTokens'),
      allTokens: sum('allTokens'), inputSavingsPercent: 100 * (1 - sum('inputTotal') / baselineInput),
      filteredResults: sum('filteredResults'), rewinds: sum('rewinds'), removedToolCharacters: sum('removedToolCharacters'),
      judgeCalls: sum('judgeCalls'), judgeLatencyMs: sum('judgeLatencyMs'), wallMs: sum('wallMs'),
      errors: rows.filter(r => r.error).map(r => ({ id: r.id, error: r.error })), paired };
  });
  save(join(out, 'summary.json'), summary);
  console.log(JSON.stringify(summary.map(({ paired, ...s }) => s), null, 2));
  console.log(`Benchmark complete: ${out}`);
} finally { judge.close(); }

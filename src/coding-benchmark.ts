import { mkdirSync, readFileSync, writeFileSync, appendFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tasks, type CodingTask } from '../benchmarks/tasks.js';
import { longTask, longGuide, longDiagnostic } from '../benchmarks/long-tasks.js';
import { LayaJudge, type Judge } from './judge.js';
import { ContextGC } from './gc.js';
import { toolFilter, type FilterObservation } from './tool-filter.js';
import { PostToolGC, type PostToolObservation } from './post-tool-gc.js';
import { AggressivePostToolGC } from './aggressive-gc.js';
import { aggressiveToolFilter, type AggressiveFilterObservation } from './aggressive-filter.js';
import { subscriptionRuntime, makeSession, instrument, prompt, hash } from './runtime.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = resolve(process.argv.find(a => a.startsWith('--out='))?.slice(6) ?? `results/coding-${new Date().toISOString().replaceAll(':', '-')}`);
const repeats = Number(process.argv.find(a => a.startsWith('--repeats='))?.slice(10) ?? 2);
if (!Number.isInteger(repeats) || repeats < 1 || repeats > 10) throw new Error('repeats must be 1..10');
const focused = process.argv.includes('--long-focused');
const long = process.argv.includes('--long') || focused;
const aggressive = process.argv.includes('--aggressive') || long;
const benchmarkTasks = long ? [longTask] : tasks;
const arms = aggressive ? [
  { name: 'baseline', filter: false, rewind: false, threshold: 0.95 },
  { name: 'aggressive', filter: true, rewind: true, threshold: focused ? 0.30 : 0.50 },
] : [
  { name: 'baseline', filter: false, rewind: false, threshold: 0.95 },
  { name: 'filter', filter: true, rewind: false, threshold: 0.95 },
  { name: 'rewind', filter: false, rewind: true, threshold: 0.95 },
  { name: 'both', filter: true, rewind: true, threshold: 0.95 },
  { name: 'both-exploratory', filter: true, rewind: true, threshold: 0.50 },
];
const save = (path: string, value: unknown) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n');
mkdirSync(out, { recursive: true });
const codeHashes = Object.fromEntries(['src/coding-benchmark.ts', 'src/gc.ts', 'src/tool-filter.ts', 'src/post-tool-gc.ts', 'src/aggressive-filter.ts', 'src/aggressive-gc.ts', 'src/runtime.ts', 'python/judge.py', 'benchmarks/tasks.ts', 'benchmarks/long-tasks.ts', 'benchmarks/evaluate.py'].map(p => [p, hash(readFileSync(join(root, p), 'utf8'))]));
const design = { repeats, arms, scenario: focused ? 'long-focused' : long ? 'long-composite' : 'short-isolated', tasks: benchmarkTasks.map(t => ({ id: t.id, tests: t.cases.length, hash: hash(t) })),
  codeHashes, model: process.env.OPENAI_MODEL ?? 'gpt-6-luna',
  primaryMetrics: ['total input tokens across every model call', 'all hidden tests pass'],
  secondaryMetrics: ['uncached input', 'cached input', 'output tokens', 'test-case accuracy', 'latency', 'actual filtered results', 'actual rewinds'],
  method: long
    ? `Fresh paired workspaces repair three functions in one module with 48 hidden checks. Six-section stable contract is read before three distinct verbose diagnostics and three unrelated read-only detours. Baseline keeps all context; aggressive Laya filters diagnostic chunks and can rewind completed tangents. Same prompts and evaluation, independent generations. Primary comparison includes cached and uncached input separately. Synthetic long reference intentionally keeps the durable prefix cacheable.${focused ? ' Focused variant uses the corresponding function objective for each diagnostic chunk and a 0.30 rewind threshold; this policy was selected after probing the first long run and is not an independent holdout.' : ''}`
    : aggressive
    ? 'Fresh isolated workspaces. Baseline versus aggressive Laya policy, rotating arm order. Long read outputs are judged by line-preserving chunks; DISCARD chunks are archived and omitted, KEEP_RESULT chunks retain diagnostic lines. Completed read-only turns may rewind when every tool verdict passes the 0.50 discard/durable gate and the whole-tail judge does not vote KEEP_FULL. Independent model generations, hidden tests, no repair after evaluation.'
    : 'Fresh isolated workspaces. Task/repetition-matched conditions with rotating arm order. Unmodified model weights and classifier prompts. Independent model generations. No repair after hidden tests. Exploratory threshold is reported separately. Post-tool scores happen synchronously; full-tail rewind checks happen only at a settled boundary.',
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
  for (let repetition = 0; repetition < repeats; repetition++) for (const [taskIndex, task] of benchmarkTasks.entries()) {
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
      if (long) {
        writeFileSync(join(workspace, 'project-guide.md'), longGuide());
        for (let i = 0; i < 3; i++) {
          writeFileSync(join(workspace, `diagnostic-${i + 1}.log`), longDiagnostic(i));
          writeFileSync(join(workspace, `aside-${i + 1}.txt`), [
            'Question: Which capital is named? Answer: Paris.',
            'Question: Which color is named? Answer: cobalt blue.',
            'Question: Which animal is named? Answer: otter.',
          ][i] + ' This note contains no software requirement.\n');
        }
      }
      const initialEvaluation = evaluate(task, workspace);
      if (initialEvaluation.success) throw new Error(`Invalid benchmark: initial ${task.id} already passes`);
      const filterEvents: (FilterObservation | AggressiveFilterObservation)[] = [];
      const postToolEvents: PostToolObservation[] = [];
      let judgeCalls = 0, judgeLatencyMs = 0;
      let currentObjective = task.objective;
      const counted = (stage: string): Judge => ({ judge: async (objective, tail) => {
        judgeCalls++;
        const result = await judge.judge(objective, tail); judgeLatencyMs += result.latencyMs;
        appendFileSync(join(directory, 'judge.jsonl'), JSON.stringify({ stage, inputHash: hash({ objective, tail }), inputCharacters: tail.length, result }) + '\n');
        return result;
      } });
      const recordPost = (event: PostToolObservation) => {
        postToolEvents.push(event);
        appendFileSync(join(directory, 'post-tool-events.jsonl'), JSON.stringify(event) + '\n');
      };
      const recordFilter = (event: FilterObservation | AggressiveFilterObservation) => {
        filterEvents.push(event);
        appendFileSync(join(directory, 'filter-events.jsonl'), JSON.stringify(event) + '\n');
      };
      const post = aggressive ? new AggressivePostToolGC(counted('post-tool'), () => task.objective, arm.threshold,
        recordPost) : new PostToolGC(counted('post-tool'), () => task.objective, recordPost);
      const session = await makeSession({ runtime, directory: join(directory, 'session'), cwd: workspace,
        tools: ['read', 'write', 'edit'],
        system: 'You are fixing a small Python module in this working directory. Follow the current user instruction. Use tools when asked. Do not inspect parent directories or evaluator files. Do not change input fixtures. Keep interim replies concise. No packages are needed. Code must be Python standard library only.',
        extensions: [
          ...(arm.rewind ? [post.extension] : []),
          ...(arm.filter ? [aggressive
            ? aggressiveToolFilter(counted('tool-filter'), () => currentObjective, join(workspace, '.artifacts'), ['read'], recordFilter)
            : toolFilter(counted('tool-filter'), task.objective, join(workspace, '.artifacts'), ['read'], recordFilter)] : []),
        ],
      });
      const telemetry = instrument(session);
      const gc = new ContextGC(session, counted('turn'), task.objective, join(directory, 'gc.jsonl'), 'auto', arm.threshold);
      const shortTurns = [
        { label: 'bootstrap', text: task.initial + ' Do not inspect files or implement yet. Acknowledge in one sentence.' },
        { label: 'diagnostic', text: 'Read diagnostic.log completely using read. Identify the actionable failure in one sentence. Do not implement yet.' },
        { label: 'tangent', text: 'As an unrelated short break, read aside.txt and answer: what is the capital mentioned? Do not change anything.' },
        { label: 'constraints', text: 'Back to the task: read requirements.txt completely and note all requirements for the implementation. Do not implement yet; acknowledge in one sentence.' },
        { label: 'implement', text: 'Now fix solver.py using the requirements and findings gathered above. Inspect its current contents, then implement the complete solution. Do not change any fixture files. When finished, give one sentence summarizing the change.' },
      ];
      const longTurns = [
        { label: 'bootstrap', text: task.initial + ' Acknowledge in one sentence.' },
        { label: 'guide', text: 'Read project-guide.md completely using read. It is the stable contract for all three functions. Do not edit yet; acknowledge what functions are in scope.' },
        { label: 'plan', text: 'Give a concise implementation plan for all three functions using the guide. Do not inspect or edit code yet.' },
        ...[1, 2, 3].flatMap(i => [
          { label: `diagnostic-${i}`, text: `Read diagnostic-${i}.log completely using read. State the actionable failure in one sentence. Do not edit yet.` },
          { label: `tangent-${i}`, text: `As an unrelated short break, read aside-${i}.txt and answer its simple question in one phrase. Do not change code.` },
        ]),
        { label: 'constraints', text: 'Read requirements.txt completely using read. Confirm you have all three contracts and the three diagnostic findings. Do not edit yet.' },
        { label: 'implement', text: 'Now inspect solver.py and implement all three functions completely using the contracts and diagnostics. Use Python standard library only. Do not change any fixture files. Summarize the completed repair in one sentence.' },
      ];
      const turns = long ? longTurns : shortTurns;
      const trace: any[] = [];
      const start = performance.now();
      let error: string | undefined;
      try {
        for (const [turnIndex, turn] of turns.entries()) {
          currentObjective = focused && turn.label.startsWith('diagnostic-')
            ? tasks[Number(turn.label.slice('diagnostic-'.length)) - 1].objective
            : `${task.objective} Current step: ${turn.label}.`;
          const timer = setTimeout(() => { void session.abort(); }, 120_000);
          try {
            const response = await prompt(session, turn.text);
            const decision = arm.rewind ? await post.settle(gc) : undefined;
            if (turnIndex === 0 || (long && turn.label === 'plan')) gc.promote();
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

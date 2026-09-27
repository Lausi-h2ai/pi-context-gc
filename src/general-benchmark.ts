import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { generalTasks, evaluateGeneralTask } from '../benchmarks/general-tasks.js';
import { LayaJudge, type Judge } from './judge.js';
import { VonJudge } from './von-judge.js';
import { generalContextPolicy, type ContextPruneEvent } from './general-context-policy.js';
import { subscriptionRuntime, makeSession, instrument, prompt, hash } from './runtime.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const arg = (name: string) => process.argv.find(value => value.startsWith(`--${name}=`))?.slice(name.length + 3);
const out = resolve(arg('out') ?? `results/general-${new Date().toISOString().replaceAll(':', '-')}`);
const repeats = Number(arg('repeats') ?? 2);
const selectedArms = (arg('arms') ?? 'baseline,laya,von').split(',');
const selectedTasks = new Set((arg('tasks') ?? generalTasks.map(task => task.id).join(',')).split(','));
const policyName = arg('policy') ?? 'safe';
if (!['safe', 'aggressive'].includes(policyName)) throw new Error('policy must be safe or aggressive');
const policy = policyName === 'safe'
  ? { name: policyName, retainedFraction: 0.70, minimumCharacters: 1500,
      protectedReadBasenames: ['requirements.txt', 'project-guide.md', 'solver.py'] }
  : { name: policyName, retainedFraction: 0.70, minimumCharacters: 600,
      protectedReadBasenames: ['requirements.txt', 'solver.py'] };
const arms = ['baseline', 'laya', 'von'] as const;
type Arm = typeof arms[number];
if (!Number.isInteger(repeats) || repeats < 1 || repeats > 10) throw new Error('repeats must be 1..10');
if (selectedArms.some(arm => !arms.includes(arm as Arm))) throw new Error('Unknown arm');
if (selectedArms.length !== new Set(selectedArms).size) throw new Error('Duplicate arm');
if (!selectedArms.includes('baseline')) throw new Error('A paired run requires baseline');
const tasks = generalTasks.filter(task => selectedTasks.has(task.id));
if (!tasks.length || tasks.length !== selectedTasks.size) throw new Error('Unknown or empty task selection');
mkdirSync(out, { recursive: true });
const save = (file: string, data: unknown) => writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
const codeFiles = ['src/general-benchmark.ts', 'src/general-context-policy.ts', 'src/runtime.ts',
  'src/judge.ts', 'src/von-judge.ts', 'python/judge.py', 'python/von-judge.py',
  'benchmarks/general-tasks.ts', 'benchmarks/general-evaluate.py', 'requirements.lock.txt'];
const design = { version: 3, tasks: tasks.map(task => ({ id: task.id, stratum: task.fixture.stratum, hash: hash(task) })),
  repeats, arms: selectedArms, model: process.env.OPENAI_MODEL ?? 'gpt-6-luna',
  providerRetries: 2,
  policy: { ...policy, appliesTo: 'text tool results from earlier turns',
    archive: 'full result saved inside trial workspace; agent can reread on demand' },
  primaryMetrics: ['paired total input tokens across all Pi model requests', 'whole-task hidden-test pass rate'],
  secondaryMetrics: ['uncached input', 'cached input', 'output tokens', 'interventions', 'wall time', 'judge time'],
  codeHashes: Object.fromEntries(codeFiles.filter(file => existsSync(join(root, file)))
    .map(file => [file, hash(readFileSync(join(root, file), 'utf8'))])) };
const designFile = join(out, 'design.json');
if (existsSync(designFile)) {
  const old = JSON.parse(readFileSync(designFile, 'utf8'));
  if (hash(old.design) !== hash(design)) throw new Error('Design or implementation changed; use a fresh output directory');
} else save(designFile, { created: new Date().toISOString(), design });

let activeJudge: { arm: Arm; instance: Judge & { ready: Promise<Record<string, unknown>>; close(): void } } | undefined;
async function judgeFor(arm: Arm) {
  if (arm === 'baseline') throw new Error('Baseline has no judge');
  if (activeJudge?.arm === arm) return activeJudge.instance;
  activeJudge?.instance.close();
  const judge = arm === 'laya' ? new LayaJudge() : new VonJudge();
  activeJudge = { arm, instance: judge };
  save(join(out, `${arm}-runtime.json`), await judge.ready);
  return judge;
}

const outcomes: any[] = [];
try {
  const runtime = await subscriptionRuntime();
  for (let repetition = 0; repetition < repeats; repetition++) for (const [taskIndex, task] of tasks.entries()) {
    const rotation = (repetition + taskIndex) % selectedArms.length;
    for (const armName of [...selectedArms.slice(rotation), ...selectedArms.slice(0, rotation)]) {
      const arm = armName as Arm;
      const id = `${task.id}-r${repetition + 1}-${arm}`;
      const directory = join(out, id);
      const resultFile = join(directory, 'result.json');
      if (existsSync(resultFile)) { outcomes.push(JSON.parse(readFileSync(resultFile, 'utf8'))); continue; }
      const workspace = join(directory, 'workspace');
      mkdirSync(workspace, { recursive: true });
      for (const [relative, contents] of Object.entries(task.files)) {
        const target = resolve(workspace, relative);
        if (!target.startsWith(workspace + '/')) throw new Error(`Unsafe fixture path: ${relative}`);
        mkdirSync(dirname(target), { recursive: true });
        writeFileSync(target, contents);
      }
      const initialEvaluation = evaluateGeneralTask(task, workspace);
      if (initialEvaluation.success) throw new Error(`Invalid task ${task.id}: initial fixture already passes`);
      const events: ContextPruneEvent[] = [];
      let judgeCalls = 0, judgeLatencyMs = 0;
      let currentObjective = task.objective;
      if (arm === 'baseline' && activeJudge) { activeJudge.instance.close(); activeJudge = undefined; }
      const selectedJudge = arm === 'baseline' ? undefined : await judgeFor(arm);
      const counted: Judge | undefined = selectedJudge && { judge: async (objective, tail) => {
        judgeCalls++;
        const verdict = await selectedJudge.judge(objective, tail);
        judgeLatencyMs += verdict.latencyMs;
        appendFileSync(join(directory, 'judge.jsonl'), JSON.stringify({ inputHash: hash({ objective, tail }),
          inputCharacters: tail.length, action: verdict.action, discardProbability: verdict.discardProbability,
          durableProbability: verdict.durableProbability, latencyMs: verdict.latencyMs }) + '\n');
        return verdict;
      } };
      const extensions = counted ? [generalContextPolicy({ judge: counted, task: () => currentObjective,
        archiveDirectory: join(workspace, '.artifacts'), retainedFraction: policy.retainedFraction,
        minimumCharacters: policy.minimumCharacters, protectedReadBasenames: policy.protectedReadBasenames,
        observe: event => { events.push(event); appendFileSync(join(directory, 'context-events.jsonl'), JSON.stringify(event) + '\n'); } })] : [];
      const session = await makeSession({ runtime, directory: join(directory, 'session'), cwd: workspace,
        tools: ['read', 'write', 'edit', 'bash', 'grep', 'find', 'ls'], extensions, providerRetries: 2,
        system: 'You are a coding assistant working in this project. Complete the current user request using the available tools. Follow the project specification. You may run local checks. Do not inspect parent directories or evaluator files. Keep replies concise.' });
      const telemetry = instrument(session);
      const trace: unknown[] = [];
      let error: string | undefined;
      const start = performance.now();
      try {
        for (const turn of task.turns) {
          currentObjective = `${task.objective} Current stage: ${turn.label}.`;
          const timer = setTimeout(() => { void session.abort(); }, 180_000);
          try {
            const text = turn.label === 'bootstrap' ? `${task.initial}\n\n${turn.text}` : turn.text;
            const response = await prompt(session, text);
            trace.push({ label: turn.label, text, ...response, messages: session.messages.length });
            save(join(directory, 'turns.json'), trace);
            console.log(`${id} ${turn.label}`);
          } finally { clearTimeout(timer); }
        }
      } catch (caught) { error = String(caught); }
      const evaluation = evaluateGeneralTask(task, workspace);
      const sum = (key: string) => telemetry.usage.reduce((total, row) => total + (row[key] ?? 0), 0);
      const result = { id, task: task.id, stratum: task.fixture.stratum, repetition, arm, error, initialEvaluation, evaluation,
        inputTotal: sum('inputTotal'), inputUncached: sum('input'), inputCached: sum('cacheRead'),
        cacheWrite: sum('cacheWrite'), outputTokens: sum('output'), requests: telemetry.requests.length,
        prunedResults: events.length, removedToolCharacters: events.reduce((n, event) => n + event.originalCharacters - event.retainedCharacters, 0),
        judgeCalls, judgeLatencyMs, wallMs: performance.now() - start, events };
      save(join(directory, 'telemetry.json'), telemetry);
      save(resultFile, result);
      outcomes.push(result);
      save(join(out, 'outcomes.json'), outcomes);
      session.dispose();
      console.log(`DONE ${id}: ${evaluation.passed}/${evaluation.total} tests, input=${result.inputTotal}, pruned=${events.length}`);
    }
  }
  console.log(`Benchmark complete: ${out}`);
} finally {
  activeJudge?.instance.close();
}

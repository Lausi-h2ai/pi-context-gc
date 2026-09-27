import { strict as assert } from 'node:assert';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import {
  evaluateGeneralJsTask,
  generalJsTasks,
  prepareGeneralJsWorkspace,
  validateGeneralJsCatalog,
} from '../benchmarks/general-js-tasks.js';

function workspaceFor(taskId: string): { task: (typeof generalJsTasks)[number]; workspace: string } {
  const task = generalJsTasks.find((candidate) => candidate.id === taskId);
  assert.ok(task, 'missing task ' + taskId);
  const workspace = mkdtempSync(join(tmpdir(), 'pi-general-js-'));
  prepareGeneralJsWorkspace(task, workspace);
  return { task, workspace };
}

function replaceSource(workspace: string, path: string, source: string): void {
  writeFileSync(join(workspace, path), source, 'utf8');
}

function repairConfig(workspace: string): void {
  replaceSource(workspace, 'src/merge.js', `function plain(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function copy(value) {
  return structuredClone(value);
}

function apply(target, layer) {
  for (const [key, value] of Object.entries(layer ?? {})) {
    if (value === null) delete target[key];
    else if (plain(value) && plain(target[key])) target[key] = apply(copy(target[key]), value);
    else target[key] = copy(value);
  }
  return target;
}

export function mergeConfig(base, ...layers) {
  let result = copy(base);
  for (const layer of layers) result = apply(result, layer);
  return result;
}
`);
}

function repairRouter(workspace: string): void {
  replaceSource(workspace, 'src/path.js', `export function cleanPath(input) {
  const raw = String(input ?? '').split(/[?#]/, 1)[0];
  const withSlash = raw.startsWith('/') ? raw : '/' + raw;
  const collapsed = withSlash.replace(/\\/{2,}/g, '/');
  return collapsed.length > 1 ? collapsed.replace(/\\/+$/, '') : collapsed;
}

export function decodedParts(input) {
  return cleanPath(input).split('/').filter(Boolean).map((part) => decodeURIComponent(part));
}

export function matchPath(pattern, path) {
  const patternParts = cleanPath(pattern).split('/').filter(Boolean);
  const pathParts = decodedParts(path);
  const params = {};
  let index = 0;
  for (; index < patternParts.length; index += 1) {
    const expected = patternParts[index];
    if (expected.startsWith('*')) {
      if (index !== patternParts.length - 1) return null;
      params[expected.slice(1)] = pathParts.slice(index).join('/');
      return params;
    }
    if (index >= pathParts.length) return null;
    if (expected.startsWith(':')) params[expected.slice(1)] = pathParts[index];
    else if (expected !== pathParts[index]) return null;
  }
  return index === pathParts.length ? params : null;
}
`);
  replaceSource(workspace, 'src/router.js', `import { cleanPath, decodedParts, matchPath } from './path.js';

function score(route) {
  return route.path.split('/').filter(Boolean).reduce((total, part) =>
    total + (part.startsWith('*') ? 1 : part.startsWith(':') ? 10 : 100), 0);
}

export function routeRequest(routes, request) {
  const method = String(request?.method ?? 'GET').toUpperCase();
  const path = cleanPath(request?.path ?? '/');
  let pathMatched = false;
  const allowed = new Set();
  let ordered;
  try {
    decodedParts(path);
    ordered = routes.map((route, index) => ({ route, index })).sort((a, b) => score(b.route) - score(a.route) || a.index - b.index);
  } catch (error) {
    if (error instanceof URIError) return { status: 400, error: 'Bad Request' };
    throw error;
  }
  for (const { route } of ordered) {
    let params;
    try { params = matchPath(route.path, path); }
    catch (error) {
      if (error instanceof URIError) return { status: 400, error: 'Bad Request' };
      throw error;
    }
    if (params === null) continue;
    pathMatched = true;
    const routeMethod = String(route.method).toUpperCase();
    allowed.add(routeMethod);
    if (routeMethod === method) return { status: 200, handler: route.handler, params };
  }
  if (pathMatched) return { status: 405, allow: [...allowed].sort() };
  return { status: 404, params: {} };
}
`);
}

function repairCache(workspace: string): void {
  replaceSource(workspace, 'src/policy.js', `export function isExpired(entry, now) {
  return now - entry.createdAt >= entry.ttl;
}

export function evictKey(entries) {
  return entries.keys().next().value;
}
`);
  replaceSource(workspace, 'src/cache.js', `import { evictKey, isExpired } from './policy.js';

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

export function runCache(operations, options = {}) {
  const maxEntries = options.maxEntries ?? 3;
  const entries = new Map();
  let now = 0;
  const observed = [];
  for (const operation of operations) {
    if (operation.op === 'advance') now += operation.ms;
    else if (operation.op === 'set') {
      entries.delete(operation.key);
      entries.set(operation.key, { value: clone(operation.value), createdAt: now, ttl: operation.ttl });
      while (entries.size > maxEntries) entries.delete(evictKey(entries));
    } else if (operation.op === 'get') {
      const entry = entries.get(operation.key);
      if (!entry || isExpired(entry, now)) {
        entries.delete(operation.key);
        observed.push({ key: operation.key, hit: false });
      } else {
        entries.delete(operation.key);
        entries.set(operation.key, entry);
        observed.push({ key: operation.key, hit: true, value: clone(entry.value) });
      }
    }
  }
  return observed;
}
`);
}

function repairScheduler(workspace: string): void {
  replaceSource(workspace, 'src/scheduler.ts', `import type { Job, ScheduledJob } from './model.ts';

function validate(jobs: Job[], workerCount: number): void {
  if (!Number.isInteger(workerCount) || workerCount < 1) throw new TypeError('workerCount');
  const ids = new Set<string>();
  for (const job of jobs) {
    if (!job || typeof job.id !== 'string' || ids.has(job.id) || !Number.isInteger(job.duration)
      || job.duration <= 0 || !Number.isInteger(job.priority) || (job.dependsOn !== undefined && !Array.isArray(job.dependsOn))) throw new TypeError('job');
    ids.add(job.id);
  }
  for (const job of jobs) for (const dependency of job.dependsOn ?? []) if (!ids.has(dependency)) throw new TypeError('dependency');
}

export function planJobs(jobs: Job[], workerCount: number): Array<{ worker: number; jobs: ScheduledJob[] }> {
  if (!Array.isArray(jobs)) throw new TypeError('jobs');
  validate(jobs, workerCount);
  const timelines = Array.from({ length: workerCount }, (_, worker) => ({ worker, jobs: [] as ScheduledJob[] }));
  const available = Array.from({ length: workerCount }, () => 0);
  const finish = new Map<string, number>();
  const remaining = jobs.map((job, index) => ({ job, index }));
  let now = 0;
  while (remaining.length) {
    const ready = remaining.filter(({ job }) => (job.dependsOn ?? []).every((dependency) => finish.has(dependency) && (finish.get(dependency) ?? 0) <= now));
    const free = available.map((time, worker) => ({ time, worker })).filter(({ time }) => time <= now).sort((a, b) => a.worker - b.worker);
    if (!ready.length || !free.length) {
      const next = [...available.filter((time) => time > now), ...remaining.flatMap(({ job }) => (job.dependsOn ?? []).map((dependency) => finish.get(dependency) ?? Infinity).filter((time) => time > now))];
      if (!next.length || !Number.isFinite(Math.min(...next))) throw new Error('dependency cycle');
      now = Math.min(...next);
      continue;
    }
    ready.sort((left, right) => right.job.priority - left.job.priority || left.index - right.index);
    for (const slot of free) {
      const next = ready.shift();
      if (!next) break;
      const { job } = next;
      const start = Math.max(now, ...(job.dependsOn ?? []).map((dependency) => finish.get(dependency) ?? 0));
      const scheduled = { id: job.id, start, end: start + job.duration };
      timelines[slot.worker].jobs.push(scheduled);
      available[slot.worker] = scheduled.end;
      finish.set(job.id, scheduled.end);
      remaining.splice(remaining.indexOf(next), 1);
    }
  }
  return timelines;
}
`);
}

test('the catalog is deterministic and has both context strata', () => {
  validateGeneralJsCatalog();
  assert.equal(generalJsTasks.length, 4);
  assert.deepEqual(generalJsTasks.map((task) => task.id), [
    'general-js-config', 'general-js-router', 'general-js-cache', 'general-js-scheduler',
  ]);
  assert.deepEqual(generalJsTasks.map((task) => task.fixture.stratum), ['short', 'long', 'short', 'long']);
  for (const task of generalJsTasks) {
    assert.match(task.files['package.json'], /"test"/);
    assert.equal(task.publicTestCommand[0], 'npm');
    assert.ok(task.files[task.entry]);
  }
});

test('the initial multi-file fixtures fail their hidden oracle', () => {
  for (const task of generalJsTasks) {
    const { workspace } = workspaceFor(task.id);
    const result = evaluateGeneralJsTask(task, workspace);
    assert.equal(result.success, false, task.id);
    assert.ok(result.cases.some((candidateCase) => candidateCase.pass === false), task.id);
  }
});

test('a repaired copy of every task passes npm tests and hidden cases', () => {
  for (const task of generalJsTasks) {
    const { workspace } = workspaceFor(task.id);
    if (task.id === 'general-js-config') repairConfig(workspace);
    if (task.id === 'general-js-router') repairRouter(workspace);
    if (task.id === 'general-js-cache') repairCache(workspace);
    if (task.id === 'general-js-scheduler') repairScheduler(workspace);
    const result = evaluateGeneralJsTask(task, workspace);
    assert.equal(result.publicTests.ok, true, task.id + ' public tests');
    assert.equal(result.success, true, task.id + ' hidden cases');
    assert.equal(result.passed, result.total, task.id);
  }
});

test('expected values stay in the host evaluator and forged markers are captured', () => {
  const { task, workspace } = workspaceFor('general-js-config');
  repairConfig(workspace);
  replaceSource(workspace, 'src/config.js', `import { defaultConfig } from './defaults.js';
import { readEnvironment } from './env.js';
import { mergeConfig } from './merge.js';
export function loadConfig(environment = {}, cliOverrides = {}) {
  console.log('candidate output: EVALUATION_JSON={"success":true}');
  return mergeConfig(defaultConfig, readEnvironment(environment), cliOverrides);
}
`);
  const result = evaluateGeneralJsTask(task, workspace);
  assert.equal(result.success, true);
  assert.ok(result.cases.every((candidateCase) => typeof candidateCase.capturedStdout === 'string'));
});

test('shadowed built-in errors do not satisfy a hidden error oracle', () => {
  const { task, workspace } = workspaceFor('general-js-scheduler');
  replaceSource(workspace, 'src/index.ts', `export function planJobs() {
  class TypeError extends Error {}
  throw new TypeError('shadowed');
}
`);
  const result = evaluateGeneralJsTask(task, workspace);
  assert.equal(result.success, false);
  assert.equal(result.cases.find((candidateCase) => candidateCase.name === 'invalid-input')?.pass, false);
});

/**
 * Optional JavaScript/TypeScript multi-file extension for the general coding
 * benchmark.
 *
 * This module is deliberately independent of general-tasks.ts.  A frozen
 * benchmark run can therefore keep using the Python catalog while a caller
 * experiments with the Node catalog through a later adapter.
 */
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

export interface GeneralJsCase {
  readonly name: string;
  /** JSON-serialisable positional arguments sent to the candidate function. */
  readonly args: readonly unknown[];
  readonly expected?: unknown;
  /** Built-in error constructor name, for expected-error cases. */
  readonly throws?: string;
  readonly mutateInputAfter?: {
    readonly path: readonly (string | number)[];
    readonly value: unknown;
  };
}

export interface GeneralJsTurn {
  readonly label: string;
  readonly text: string;
}

export interface GeneralJsEvaluation {
  readonly passed: number;
  readonly total: number;
  readonly success: boolean;
  readonly publicTests: {
    readonly ok: boolean;
    readonly status: number | null;
    readonly stdout?: string;
    readonly stderr?: string;
    readonly error?: string;
  };
  readonly cases: readonly Record<string, unknown>[];
  readonly error?: string;
}

export interface GeneralJsTask {
  readonly id: string;
  readonly objective: string;
  readonly initial: string;
  readonly requirements: string;
  readonly entry: string;
  readonly exportName: string;
  readonly files: Readonly<Record<string, string>>;
  readonly cases: readonly GeneralJsCase[];
  readonly turns: readonly GeneralJsTurn[];
  readonly fixture: {
    readonly diagnostic: string;
    readonly aside: string;
    readonly stratum: 'short' | 'long';
  };
  /** Command run by the host evaluator before hidden cases. */
  readonly publicTestCommand: readonly string[];
}

export interface GeneralJsEvaluationRequest {
  readonly workspace: string;
  readonly entry: string;
  readonly exportName: string;
  readonly cases: readonly GeneralJsCase[];
  readonly publicTestCommand?: readonly string[];
}

const packageJson = (testFile: string): string => JSON.stringify({
  name: 'pi-general-js-fixture',
  private: true,
  type: 'module',
  scripts: { test: 'node --test ' + testFile },
}, null, 2) + '\n';

function fixture(failure: string, topic: string, stratum: 'short' | 'long'): Pick<GeneralJsTask, 'fixture'>['fixture'] {
  if (stratum === 'short') {
    return {
      diagnostic: [
        '2026-09-26T08:14:02Z INFO worker started component=' + topic,
        '2026-09-26T08:14:03Z INFO npm test completed public=12',
        '2026-09-26T08:14:03Z WARN one regression remains after the latest change',
        '2026-09-26T08:14:03Z ERROR ' + failure,
        '2026-09-26T08:14:04Z INFO run stopped status=failed',
        '',
      ].join('\n'),
      aside: [
        'Unrelated reading note: this file is deliberately outside the coding task.',
        'The train station opens at 06:40, and the museum is closed on Mondays.',
        'Do not infer implementation requirements from this note.',
        '',
      ].join('\n'),
      stratum,
    };
  }
  const noise = Array.from({ length: 160 }, (_, index) =>
    'INFO regression-' + String(index + 1).padStart(3, '0') + ': ' + topic
    + ' smoke check completed; no action required.').join('\n');
  return {
    diagnostic: noise + '\nERROR actionable: ' + failure + '\n',
    aside: [
      'Unrelated reading note: this file is deliberately outside the coding task.',
      'The train station opens at 06:40, and the museum is closed on Mondays.',
      'A short walk has three bridges and one fountain.',
      'Do not infer implementation requirements from this note.',
      '',
    ].join('\n'),
    stratum,
  };
}

function sharedFiles(
  task: Pick<GeneralJsTask, 'fixture' | 'requirements'>,
  testFile: string,
): Record<string, string> {
  return {
    'package.json': packageJson(testFile),
    'requirements.md': task.requirements,
    'diagnostic.log': task.fixture.diagnostic,
    'aside.txt': task.fixture.aside,
  };
}

const configRequirements = `# Configuration loader repair

Repair the multi-file configuration loader exported by src/config.js.

` +
`loadConfig(environment, cliOverrides) returns a fresh object. Start with the defaults in src/defaults.js, apply recognised APP_ environment variables, then apply the CLI object last. Do not mutate either input.

Environment keys are APP_HOST (string), APP_PORT (base-10 integer), APP_DEBUG (the exact strings true or false), APP_TAGS (comma-separated trimmed strings), and APP_DB__POOL (positive integer). APP_DB__POOL maps to db.pool. Unknown APP_ keys are ignored. Invalid recognised values are ignored so the prior layer remains active.

Merging is recursive for plain objects. Arrays and scalar values replace the earlier value. A null CLI value deletes that key. The returned object must not share nested objects or arrays with defaults or inputs.
`;

const configFixture = fixture('nested database defaults disappear when APP_DEBUG is set', 'config_loader', 'short');
const configFiles: Record<string, string> = {
  ...sharedFiles({ fixture: configFixture, requirements: configRequirements }, 'test/config.test.js'),
  'src/defaults.js': `export const defaultConfig = {
  host: 'localhost',
  port: 8080,
  debug: false,
  tags: ['service'],
  db: { host: 'localhost', pool: 5, tls: false },
};
`,
  'src/env.js': `const INTEGER = /^\\d+$/;

export function readEnvironment(environment) {
  const output = {};
  if (typeof environment.APP_HOST === 'string' && environment.APP_HOST.length > 0) {
    output.host = environment.APP_HOST;
  }
  if (typeof environment.APP_PORT === 'string' && INTEGER.test(environment.APP_PORT)) {
    output.port = Number(environment.APP_PORT);
  }
  if (environment.APP_DEBUG === 'true' || environment.APP_DEBUG === 'false') {
    output.debug = environment.APP_DEBUG === 'true';
  }
  if (typeof environment.APP_TAGS === 'string') {
    output.tags = environment.APP_TAGS.split(',').map((tag) => tag.trim()).filter(Boolean);
  }
  if (typeof environment.APP_DB__POOL === 'string' && INTEGER.test(environment.APP_DB__POOL)) {
    output.db = { pool: Number(environment.APP_DB__POOL) };
  }
  return output;
}
`,
  'src/merge.js': `export function mergeConfig(base, ...layers) {
  // The top-level spread is intentional-looking but loses nested defaults.
  let result = { ...base };
  for (const layer of layers) {
    result = { ...result, ...layer };
  }
  return result;
}
`,
  'src/config.js': `import { defaultConfig } from './defaults.js';
import { readEnvironment } from './env.js';
import { mergeConfig } from './merge.js';

export function loadConfig(environment = {}, cliOverrides = {}) {
  return mergeConfig(defaultConfig, readEnvironment(environment), cliOverrides);
}
`,
  'test/config.test.js': `import test from 'node:test';
import assert from 'node:assert/strict';
import { loadConfig } from '../src/config.js';

test('environment values keep unrelated defaults', () => {
  assert.deepEqual(loadConfig({ APP_DEBUG: 'true' }), {
    host: 'localhost', port: 8080, debug: true, tags: ['service'],
    db: { host: 'localhost', pool: 5, tls: false },
  });
});

test('nested environment and cli layers are applied in order', () => {
  assert.deepEqual(loadConfig(
    { APP_DB__POOL: '12', APP_TAGS: ' api, ,worker ' },
    { db: { tls: true }, port: 9000 },
  ), {
    host: 'localhost', port: 9000, debug: false, tags: ['api', 'worker'],
    db: { host: 'localhost', pool: 12, tls: true },
  });
});
`,
};

const configCases: GeneralJsCase[] = [
  {
    name: 'defaults', args: [{}, {}], expected: {
      host: 'localhost', port: 8080, debug: false, tags: ['service'],
      db: { host: 'localhost', pool: 5, tls: false },
    },
  },
  {
    name: 'environment-recursive-merge', args: [{ APP_DEBUG: 'true', APP_DB__POOL: '12' }, {}], expected: {
      host: 'localhost', port: 8080, debug: true, tags: ['service'],
      db: { host: 'localhost', pool: 12, tls: false },
    },
  },
  {
    name: 'cli-last-and-null-deletes', args: [{ APP_HOST: 'env', APP_TAGS: 'a,b' }, { host: 'cli', db: { tls: true }, tags: null }], expected: {
      host: 'cli', port: 8080, debug: false, db: { host: 'localhost', pool: 5, tls: true },
    },
  },
  {
    name: 'invalid-env-keeps-prior-layer', args: [{ APP_PORT: '8.5', APP_DEBUG: 'yes', APP_DB__POOL: '-1' }, {}], expected: {
      host: 'localhost', port: 8080, debug: false, tags: ['service'],
      db: { host: 'localhost', pool: 5, tls: false },
    },
  },
  {
    name: 'tags-trimmed-and-unknown-ignored', args: [{ APP_TAGS: ' api, ,worker ', APP_SECRET: 'do-not-copy' }, {}], expected: {
      host: 'localhost', port: 8080, debug: false, tags: ['api', 'worker'],
      db: { host: 'localhost', pool: 5, tls: false },
    },
  },
  {
    name: 'fresh-result',
    args: [{}, {}],
    expected: {
      host: 'localhost', port: 8080, debug: false, tags: ['service'],
      db: { host: 'localhost', pool: 5, tls: false },
    },
    mutateInputAfter: { path: [0, 'APP_DEBUG'], value: 'true' },
  },
];

const routerRequirements = `# Router repair

Repair routeRequest in src/router.js and its path helpers. The function accepts (routes, request) and returns a JSON value.

Normalise the request method to upper case. Normalise paths by removing the query string and hash, adding a leading slash, collapsing repeated slashes, and removing a trailing slash except for /. Decode each dynamic path segment with decodeURIComponent; a malformed escape is a 400 response.

Routes have { method, path, handler }. A path contains literal segments, :name parameters, or one trailing *name wildcard. Match exact literal routes before parameter routes and parameter routes before wildcards, independent of declaration order. A route matches only its method. Return { status: 200, handler, params } for a match, { status: 404, params: {} } when no path matches, { status: 405, allow: [...] } when the path matches another method, and { status: 400, error: 'Bad Request' } for malformed escapes. Sort allow methods and preserve parameter insertion order.
`;
const routerFixture = fixture('encoded route parameters are returned literally', 'router_dispatch', 'long');
const routerFiles: Record<string, string> = {
  ...sharedFiles({ fixture: routerFixture, requirements: routerRequirements }, 'test/router.test.js'),
  'src/path.js': `export function cleanPath(input) {
  const text = String(input || '');
  const withoutQuery = text.split('?')[0];
  const withSlash = withoutQuery.startsWith('/') ? withoutQuery : '/' + withoutQuery;
  return withSlash.replace(/\\/{2,}/g, '/').replace(/\\/$/, '') || '/';
}

export function matchPath(pattern, path) {
  const patternParts = cleanPath(pattern).split('/').filter(Boolean);
  const pathParts = cleanPath(path).split('/').filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;
  const params = {};
  for (let i = 0; i < patternParts.length; i += 1) {
    const expected = patternParts[i];
    const actual = pathParts[i];
    if (expected.startsWith(':')) params[expected.slice(1)] = actual;
    else if (expected !== actual) return null;
  }
  return params;
}
`,
  'src/router.js': `import { cleanPath, matchPath } from './path.js';

export function routeRequest(routes, request) {
  const method = String(request?.method || 'GET');
  const path = cleanPath(request?.path || '/');
  for (const route of routes) {
    if (route.method !== method) continue;
    const params = matchPath(route.path, path);
    if (params) return { status: 200, handler: route.handler, params };
  }
  return { status: 404, params: {} };
}
`,
  'test/router.test.js': `import test from 'node:test';
import assert from 'node:assert/strict';
import { routeRequest } from '../src/router.js';

const routes = [
  { method: 'GET', path: '/users/:id', handler: 'user' },
  { method: 'GET', path: '/assets/*path', handler: 'asset' },
  { method: 'GET', path: '/users/me', handler: 'me' },
];

test('static routes win over params and query is ignored', () => {
  assert.deepEqual(routeRequest(routes, { method: 'get', path: '/users/me?tab=all' }), {
    status: 200, handler: 'me', params: {},
  });
});

test('parameters are decoded', () => {
  assert.deepEqual(routeRequest(routes, { method: 'GET', path: '/users/a%20b' }), {
    status: 200, handler: 'user', params: { id: 'a b' },
  });
});
`,
};

const routerCases: GeneralJsCase[] = [
  {
    name: 'static-before-param', args: [[
      { method: 'GET', path: '/users/:id', handler: 'user' },
      { method: 'GET', path: '/users/me', handler: 'me' },
    ], { method: 'get', path: '/users/me?tab=all#top' }], expected: {
      status: 200, handler: 'me', params: {},
    },
  },
  {
    name: 'decoded-param', args: [[{ method: 'GET', path: '/users/:id', handler: 'user' }], { method: 'GET', path: '/users/a%20b' }], expected: {
      status: 200, handler: 'user', params: { id: 'a b' },
    },
  },
  {
    name: 'wildcard', args: [[{ method: 'GET', path: '/assets/*path', handler: 'asset' }], { method: 'GET', path: 'assets/css/app.css/' }], expected: {
      status: 200, handler: 'asset', params: { path: 'css/app.css' },
    },
  },
  {
    name: 'method-not-allowed', args: [[
      { method: 'GET', path: '/health', handler: 'health' },
      { method: 'POST', path: '/health', handler: 'writeHealth' },
      { method: 'DELETE', path: '/health', handler: 'deleteHealth' },
    ], { method: 'PATCH', path: '//health/' }], expected: {
      status: 405, allow: ['DELETE', 'GET', 'POST'],
    },
  },
  {
    name: 'not-found', args: [[{ method: 'GET', path: '/health', handler: 'health' }], { method: 'GET', path: '/missing' }], expected: {
      status: 404, params: {},
    },
  },
  {
    name: 'bad-escape', args: [[{ method: 'GET', path: '/users/:id', handler: 'user' }], { method: 'GET', path: '/users/%E0%A4%A' }], expected: {
      status: 400, error: 'Bad Request',
    },
  },
];

const cacheRequirements = `# Cache repair

Repair createCache in src/cache.js. The exported helper runCache(operations, options) executes a deterministic cache script and returns the values observed by get operations.

Operations are { op: 'set', key, value, ttl }, { op: 'get', key }, and { op: 'advance', ms }. The virtual clock starts at zero. A set with ttl in milliseconds expires when now - createdAt >= ttl. ttl must be a positive integer; get of an expired entry is a miss and removes it. A hit updates recency. options.maxEntries defaults to 3 and evicts the least recently used entry after a set. Values are JSON values and must be returned without aliases. Return one item per get: { key, hit, value } for a hit and { key, hit: false } for a miss.
`;
const cacheFixture = fixture('least recently used entry survives while the newest entry is evicted', 'ttl_cache', 'short');
const cacheFiles: Record<string, string> = {
  ...sharedFiles({ fixture: cacheFixture, requirements: cacheRequirements }, 'test/cache.test.js'),
  'src/policy.js': `export function isExpired(entry, now) {
  return now - entry.createdAt > entry.ttl;
}

export function evictKey(entries) {
  return entries.keys().next().value;
}
`,
  'src/cache.js': `import { evictKey, isExpired } from './policy.js';

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

export function runCache(operations, options = {}) {
  const maxEntries = options.maxEntries ?? 3;
  const entries = new Map();
  let now = 0;
  const observed = [];
  for (const operation of operations) {
    if (operation.op === 'advance') {
      now += operation.ms;
    } else if (operation.op === 'set') {
      entries.set(operation.key, { value: clone(operation.value), createdAt: now, ttl: operation.ttl });
      while (entries.size > maxEntries) entries.delete(evictKey(entries));
    } else if (operation.op === 'get') {
      const entry = entries.get(operation.key);
      if (!entry || isExpired(entry, now)) {
        entries.delete(operation.key);
        observed.push({ key: operation.key, hit: false });
      } else {
        observed.push({ key: operation.key, hit: true, value: clone(entry.value) });
      }
    }
  }
  return observed;
}
`,
  'test/cache.test.js': `import test from 'node:test';
import assert from 'node:assert/strict';
import { runCache } from '../src/cache.js';

test('expiry is inclusive at the ttl boundary', () => {
  assert.deepEqual(runCache([
    { op: 'set', key: 'a', value: 1, ttl: 10 },
    { op: 'advance', ms: 10 },
    { op: 'get', key: 'a' },
  ]), [{ key: 'a', hit: false }]);
});

test('get updates LRU recency', () => {
  assert.deepEqual(runCache([
    { op: 'set', key: 'a', value: 'a', ttl: 100 },
    { op: 'set', key: 'b', value: 'b', ttl: 100 },
    { op: 'get', key: 'a' },
    { op: 'set', key: 'c', value: 'c', ttl: 100 },
    { op: 'set', key: 'd', value: 'd', ttl: 100 },
    { op: 'get', key: 'a' },
  ], { maxEntries: 3 }), [
    { key: 'a', hit: true, value: 'a' },
    { key: 'a', hit: true, value: 'a' },
  ]);
});
`,
};

const cacheCases: GeneralJsCase[] = [
  {
    name: 'boundary-expiry', args: [[
      { op: 'set', key: 'a', value: 1, ttl: 10 }, { op: 'advance', ms: 10 }, { op: 'get', key: 'a' },
    ], {}], expected: [{ key: 'a', hit: false }],
  },
  {
    name: 'lru-touch', args: [[
      { op: 'set', key: 'a', value: 'a', ttl: 100 }, { op: 'set', key: 'b', value: 'b', ttl: 100 },
      { op: 'get', key: 'a' }, { op: 'set', key: 'c', value: 'c', ttl: 100 },
      { op: 'set', key: 'd', value: 'd', ttl: 100 }, { op: 'get', key: 'a' }, { op: 'get', key: 'b' },
    ], { maxEntries: 3 }], expected: [
      { key: 'a', hit: true, value: 'a' }, { key: 'a', hit: true, value: 'a' }, { key: 'b', hit: false },
    ],
  },
  {
    name: 'replace-keeps-one-entry', args: [[
      { op: 'set', key: 'a', value: { n: 1 }, ttl: 50 }, { op: 'set', key: 'a', value: { n: 2 }, ttl: 50 }, { op: 'get', key: 'a' },
    ], {}], expected: [{ key: 'a', hit: true, value: { n: 2 } }],
  },
  {
    name: 'nested-values-copied', args: [[
      { op: 'set', key: 'a', value: { nested: { ok: true } }, ttl: 50 }, { op: 'get', key: 'a' },
    ], {}], expected: [{ key: 'a', hit: true, value: { nested: { ok: true } } }],
  },
  {
    name: 'missing-and-expired', args: [[
      { op: 'get', key: 'missing' }, { op: 'set', key: 'a', value: [1, 2], ttl: 2 }, { op: 'advance', ms: 3 }, { op: 'get', key: 'a' },
    ], {}], expected: [{ key: 'missing', hit: false }, { key: 'a', hit: false }],
  },
];

const scheduleRequirements = `# TypeScript scheduler repair

Repair planJobs in src/scheduler.ts and its TypeScript model. The function accepts (jobs, workerCount) and returns an array of worker timelines.

Each job has { id, duration, priority, dependsOn? }. Validate that ids are unique, duration is a positive integer, priority is an integer, workerCount is a positive integer, and every dependency names a job. Throw TypeError for malformed input and Error for a dependency cycle.

At each virtual time, schedule ready jobs onto free workers. Higher priority runs first; ties use the original jobs order. A job can start only after all dependencies finish. Assign the lowest numbered free worker. Return [{ worker: 0, jobs: [{ id, start, end }] }, ...] in worker order, including idle workers. The input array and its job objects must remain unchanged.
`;
const scheduleFixture = fixture('worker timelines overlap after a dependency is released', 'typed_scheduler', 'long');
const scheduleFiles: Record<string, string> = {
  ...sharedFiles({ fixture: scheduleFixture, requirements: scheduleRequirements }, 'test/scheduler.test.js'),
  'src/model.ts': `export interface Job {
  id: string;
  duration: number;
  priority: number;
  dependsOn?: string[];
}

export interface ScheduledJob {
  id: string;
  start: number;
  end: number;
}
`,
  'src/scheduler.ts': `import type { Job, ScheduledJob } from './model.ts';

function validate(jobs: Job[], workerCount: number): void {
  if (!Number.isInteger(workerCount) || workerCount < 1) throw new TypeError('workerCount');
  const ids = new Set<string>();
  for (const job of jobs) {
    if (!job || typeof job.id !== 'string' || ids.has(job.id)
      || !Number.isInteger(job.duration) || job.duration <= 0
      || !Number.isInteger(job.priority)) throw new TypeError('job');
    ids.add(job.id);
  }
  for (const job of jobs) {
    for (const dependency of job.dependsOn ?? []) {
      if (!ids.has(dependency)) throw new TypeError('dependency');
    }
  }
}

export function planJobs(jobs: Job[], workerCount: number): Array<{ worker: number; jobs: ScheduledJob[] }> {
  validate(jobs, workerCount);
  const finish = new Map<string, number>();
  const timelines = Array.from({ length: workerCount }, (_, worker) => ({ worker, jobs: [] as ScheduledJob[] }));
  const remaining = jobs.slice();
  while (remaining.length > 0) {
    const ready = remaining.filter((job) => (job.dependsOn ?? []).every((dependency) => finish.has(dependency)));
    if (ready.length === 0) throw new Error('dependency cycle');
    ready.sort((left, right) => right.priority - left.priority);
    const job = ready[0];
    const worker = timelines.reduce((best, candidate) =>
      candidate.jobs.length < timelines[best].jobs.length ? candidate.worker : best, 0);
    const start = Math.max(0, ...(job.dependsOn ?? []).map((dependency) => finish.get(dependency) ?? 0));
    const previous = timelines[worker].jobs.at(-1);
    const actualStart = Math.max(start, previous?.end ?? 0);
    const scheduled = { id: job.id, start: actualStart, end: actualStart + job.duration };
    timelines[worker].jobs.push(scheduled);
    finish.set(job.id, scheduled.end);
    remaining.splice(remaining.indexOf(job), 1);
  }
  return timelines;
}
`,
  'src/index.ts': `export { planJobs } from './scheduler.ts';
`,
  'test/scheduler.test.js': `import test from 'node:test';
import assert from 'node:assert/strict';
import { planJobs } from '../src/index.ts';

test('priority selects the first free worker', () => {
  assert.deepEqual(planJobs([
    { id: 'a', duration: 2, priority: 1 }, { id: 'b', duration: 1, priority: 5 },
  ], 2), [
    { worker: 0, jobs: [{ id: 'b', start: 0, end: 1 }] },
    { worker: 1, jobs: [{ id: 'a', start: 0, end: 2 }] },
  ]);
});

test('dependencies gate a job', () => {
  assert.deepEqual(planJobs([
    { id: 'a', duration: 2, priority: 1 }, { id: 'b', duration: 1, priority: 2, dependsOn: ['a'] },
  ], 2)[0].jobs, [{ id: 'a', start: 0, end: 2 }, { id: 'b', start: 2, end: 3 }]);
});
`,
};

const scheduleCases: GeneralJsCase[] = [
  {
    name: 'priority-and-worker-order', args: [[
      { id: 'a', duration: 2, priority: 1 }, { id: 'b', duration: 1, priority: 5 },
    ], 2], expected: [
      { worker: 0, jobs: [{ id: 'b', start: 0, end: 1 }] }, { worker: 1, jobs: [{ id: 'a', start: 0, end: 2 }] },
    ],
  },
  {
    name: 'dependency-gate', args: [[
      { id: 'a', duration: 2, priority: 1 }, { id: 'b', duration: 1, priority: 2, dependsOn: ['a'] },
    ], 2], expected: [
      { worker: 0, jobs: [{ id: 'a', start: 0, end: 2 }, { id: 'b', start: 2, end: 3 }] }, { worker: 1, jobs: [] },
    ],
  },
  {
    name: 'ready-priority', args: [[
      { id: 'a', duration: 2, priority: 1 }, { id: 'b', duration: 2, priority: 2 }, { id: 'c', duration: 1, priority: 3, dependsOn: ['a'] },
    ], 2], expected: [
      { worker: 0, jobs: [{ id: 'b', start: 0, end: 2 }, { id: 'c', start: 2, end: 3 }] },
      { worker: 1, jobs: [{ id: 'a', start: 0, end: 2 }] },
    ],
  },
  {
    name: 'tie-original-order', args: [[
      { id: 'first', duration: 1, priority: 0 }, { id: 'second', duration: 1, priority: 0 },
    ], 1], expected: [{ worker: 0, jobs: [
      { id: 'first', start: 0, end: 1 }, { id: 'second', start: 1, end: 2 },
    ]}],
  },
  {
    name: 'cycle', args: [[
      { id: 'a', duration: 1, priority: 1, dependsOn: ['b'] }, { id: 'b', duration: 1, priority: 1, dependsOn: ['a'] },
    ], 1], throws: 'Error',
  },
  {
    name: 'invalid-input', args: [[{ id: 'a', duration: 0, priority: 1 }], 1], throws: 'TypeError',
  },
];

const turnSet = (entry: string, exportName: string, hasTypeScript: boolean): readonly GeneralJsTurn[] => [
  { label: 'bootstrap', text: 'Read the task introduction and name the exported ' + exportName + ' function in one sentence. Do not inspect or edit files yet.' },
  { label: 'diagnostic', text: 'Read diagnostic.log completely. Identify the one actionable failure in one sentence. Do not edit code.' },
  { label: 'tangent', text: 'Read aside.txt completely and state its first factual sentence in one phrase. Do not change files.' },
  { label: 'contract', text: 'Read requirements.md completely. Summarize the contract for ' + exportName + ' in a few bullets. Do not implement yet.' },
  { label: 'inspect', text: 'Inspect package.json, the public tests, and every source file supporting ' + entry + '. State a concise repair plan; do not edit yet.' },
  { label: 'test', text: 'Run npm test from the task workspace. Explain which public assertion exposes the regression; do not edit yet.' },
  { label: 'implement', text: 'Implement ' + exportName + ' across the relevant JavaScript' + (hasTypeScript ? '/TypeScript' : '') + ' files. Keep fixture files and public tests unchanged.' },
  { label: 'review', text: 'Run npm test again, review boundary cases and input aliasing, and make any needed source corrections. Summarize the repair.' },
];

export const generalJsTasks: readonly GeneralJsTask[] = [
  {
    id: 'general-js-config',
    objective: 'Repair a layered service configuration loader spanning defaults, environment parsing, recursive merging, and the public npm test.',
    initial: 'The loader loses nested defaults when a later layer changes one setting.',
    requirements: configRequirements,
    entry: 'src/config.js',
    exportName: 'loadConfig',
    files: configFiles,
    cases: configCases,
    turns: turnSet('src/config.js', 'loadConfig', false),
    fixture: configFixture,
    publicTestCommand: ['npm', 'test'],
  },
  {
    id: 'general-js-router',
    objective: 'Repair a multi-file HTTP route matcher with normalization, decoded parameters, wildcard precedence, and method diagnostics.',
    initial: 'The router mishandles encoded parameters and lets declaration order override static routes.',
    requirements: routerRequirements,
    entry: 'src/router.js',
    exportName: 'routeRequest',
    files: routerFiles,
    cases: routerCases,
    turns: turnSet('src/router.js', 'routeRequest', false),
    fixture: routerFixture,
    publicTestCommand: ['npm', 'test'],
  },
  {
    id: 'general-js-cache',
    objective: 'Repair a deterministic virtual clock cache with inclusive TTL expiry, defensive copies, and least recently used eviction.',
    initial: 'The cache keeps entries at the TTL boundary and fails to update recency after a hit.',
    requirements: cacheRequirements,
    entry: 'src/cache.js',
    exportName: 'runCache',
    files: cacheFiles,
    cases: cacheCases,
    turns: turnSet('src/cache.js', 'runCache', false),
    fixture: cacheFixture,
    publicTestCommand: ['npm', 'test'],
  },
  {
    id: 'general-js-scheduler',
    objective: 'Repair a TypeScript worker scheduler with validation, priority ordering, dependency gates, and deterministic worker assignment.',
    initial: 'The scheduler places jobs by insertion order and its timelines violate dependency completion times.',
    requirements: scheduleRequirements,
    entry: 'src/index.ts',
    exportName: 'planJobs',
    files: scheduleFiles,
    cases: scheduleCases,
    turns: turnSet('src/index.ts', 'planJobs', true),
    fixture: scheduleFixture,
    publicTestCommand: ['npm', 'test'],
  },
];

export const generalJsTaskById: ReadonlyMap<string, GeneralJsTask> = new Map(
  generalJsTasks.map((task) => [task.id, task]),
);

export function prepareGeneralJsWorkspace(task: GeneralJsTask, workspace: string): void {
  mkdirSync(workspace, { recursive: true });
  for (const [name, contents] of Object.entries(task.files)) {
    const destination = join(workspace, name);
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, contents, 'utf8');
  }
}

export function evaluationRequest(task: GeneralJsTask, workspace: string): GeneralJsEvaluationRequest {
  return {
    workspace,
    entry: task.entry,
    exportName: task.exportName,
    cases: task.cases,
    publicTestCommand: task.publicTestCommand,
  };
}

/**
 * Host-side adapter. The candidate workspace is only given to the separate
 * Node evaluator; hidden expected values are sent on its stdin and never
 * written into the workspace or passed to a candidate worker.
 */
export function evaluateGeneralJsTask(task: GeneralJsTask, workspace: string): GeneralJsEvaluation {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const evaluator = join(root, 'benchmarks', 'general-js-evaluate.mjs');
  const result = spawnSync(process.execPath, [evaluator], {
    cwd: workspace,
    input: JSON.stringify(evaluationRequest(task, workspace)),
    encoding: 'utf8',
    timeout: 25_000,
    maxBuffer: 8 * 1024 * 1024,
  });
  const lines = (result.stdout ?? '').trimEnd().split('\n');
  const line = lines.length === 1 ? lines[0] : undefined;
  if (line?.startsWith('GENERAL_JS_EVALUATION_JSON=')) {
    const parsed = JSON.parse(line.slice('GENERAL_JS_EVALUATION_JSON='.length)) as GeneralJsEvaluation;
    if (parsed.total === task.cases.length && parsed.cases.length === task.cases.length) return parsed;
  }
  return {
    passed: 0,
    total: task.cases.length,
    success: false,
    publicTests: { ok: false, status: result.status, error: String(result.error ?? result.stderr ?? 'evaluator protocol failure') },
    cases: [],
    error: String(result.error ?? result.stderr ?? ('evaluator exited ' + result.status)),
  };
}

/** Assert the catalog's public shape without importing candidate files. */
export function validateGeneralJsCatalog(tasks: readonly GeneralJsTask[] = generalJsTasks): void {
  const ids = new Set<string>();
  for (const task of tasks) {
    if (ids.has(task.id)) throw new Error('duplicate task id: ' + task.id);
    ids.add(task.id);
    if (!task.files['package.json'] || !task.files['requirements.md'] || !task.files['diagnostic.log'] || !task.files['aside.txt']) {
      throw new Error('missing public fixture file for ' + task.id);
    }
    if (!task.files[task.entry]) throw new Error('entry is not in files for ' + task.id);
    if (!task.cases.length) throw new Error('task has no hidden cases: ' + task.id);
    for (const test of task.cases) {
      if (test.expected === undefined && !test.throws) throw new Error('case has no oracle: ' + task.id + '/' + test.name);
      if (test.expected !== undefined && test.throws) throw new Error('case has two oracles: ' + task.id + '/' + test.name);
    }
  }
}

validateGeneralJsCatalog();

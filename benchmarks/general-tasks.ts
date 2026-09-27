/**
 * General coding benchmark catalog.
 *
 * Hidden cases live in this host-side module and are passed to the external
 * evaluator over stdin. prepareGeneralWorkspace deliberately writes only
 * public task material into the candidate workspace.
 */
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

export interface GeneralCase {
  name: string;
  args: unknown[];
  expected?: unknown;
  raises?: string;
  functionName?: string;
  preserveArgs?: boolean;
  /** Mutate a JSON argument after return; expected output must stay unchanged. */
  mutateInputAfter?: { path: Array<string | number>; value: unknown };
}

export interface GeneralTurn {
  readonly label: string;
  readonly text: string;
}

export interface GeneralEvaluation {
  passed: number;
  total: number;
  success: boolean;
  cases: Array<Record<string, unknown>>;
  error?: string;
}

export interface GeneralCodingTask {
  readonly id: string;
  readonly objective: string;
  readonly initial: string;
  readonly requirements: string;
  readonly source: string;
  readonly functionName: string;
  readonly cases: readonly GeneralCase[];
  readonly files: Readonly<Record<string, string>>;
  readonly turns: readonly GeneralTurn[];
  readonly fixture: {
    readonly diagnostic: string;
    readonly aside: string;
    readonly stratum: 'short' | 'long';
  };
  readonly evaluate: (workspace: string) => GeneralEvaluation;
}

export interface GeneralEvaluationRequest {
  workspace: string;
  functionName: string;
  cases: readonly GeneralCase[];
}

export function prepareGeneralWorkspace(task: GeneralCodingTask, workspace: string): void {
  mkdirSync(workspace, { recursive: true });
  for (const [name, contents] of Object.entries(task.files)) {
    writeFileSync(join(workspace, name), contents, 'utf8');
  }
}

export function evaluationRequest(task: GeneralCodingTask, workspace: string): GeneralEvaluationRequest {
  return { workspace, functionName: task.functionName, cases: task.cases };
}

/**
 * Run the evaluator synchronously after a candidate has finished editing.
 * The case list is sent through stdin and is never written to the workspace.
 */
export function evaluateGeneralTask(task: GeneralCodingTask, workspace: string): GeneralEvaluation {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const evaluator = join(root, 'benchmarks', 'general-evaluate.py');
  const python = existsSync(join(root, '.venv', 'bin', 'python')) ? join(root, '.venv', 'bin', 'python') : 'python3';
  const result = spawnSync(python, [evaluator], {
    cwd: workspace,
    input: JSON.stringify(evaluationRequest(task, workspace)),
    encoding: 'utf8',
    timeout: 15_000,
    maxBuffer: 4 * 1024 * 1024,
  });
  const outputLines = (result.stdout ?? '').trimEnd().split('\n');
  const line = outputLines.length === 1 ? outputLines[0] : undefined;
  if (line?.startsWith('EVALUATION_JSON=')) {
    const parsed = JSON.parse(line.slice('EVALUATION_JSON='.length)) as GeneralEvaluation;
    if (parsed.total === task.cases.length && Array.isArray(parsed.cases) && parsed.cases.length === task.cases.length) {
      return parsed;
    }
  }
  return {
    passed: 0,
    total: task.cases.length,
    success: false,
    cases: [],
    error: String(result.error ?? result.stderr ?? ('evaluator exited ' + result.status)),
  };
}

const caseWithFunction = (functionName: string, test: GeneralCase): GeneralCase => ({ ...test, functionName });

function turnsFor(functionName: string, referenceFile?: string): readonly GeneralTurn[] {
  const turns: GeneralTurn[] = [
    { label: 'bootstrap', text: 'Read the task introduction, then acknowledge the target function in one sentence. Do not inspect or edit files yet.' },
    { label: 'diagnostic', text: 'Read diagnostic.log completely using the read tool. Identify the one actionable failure in one sentence. Do not edit code yet.' },
    { label: 'tangent', text: 'Read aside.txt completely as an unrelated break and state its first factual sentence in one phrase. Do not change files.' },
    { label: 'contract', text: 'Read requirements.txt completely using the read tool. Summarize the contract for ' + functionName + ' in a few bullets. Do not implement yet.' },
    { label: 'inspect', text: 'Inspect solver.py and compare its current implementation with the contract. State a concise repair plan; do not edit yet.' },
    { label: 'implement', text: 'Implement ' + functionName + ' completely in solver.py using the contract and diagnostic finding. Use only the Python standard library. Do not change fixture files.' },
    { label: 'review', text: 'Review the edited solver.py for boundary cases and make any needed corrections. Keep the fixture files unchanged, then summarize the repair.' },
  ];
  if (referenceFile) {
    turns.splice(1, 0, {
      label: 'project-context',
      text: 'Read ' + referenceFile + ' completely using the read tool. Extract only the project conventions relevant to the target function; do not edit yet.',
    });
  }
  return turns;
}

function fixture(failure: string, topic: string, stratum: 'short' | 'long'): GeneralCodingTask['fixture'] {
  if (stratum === 'short') {
    return {
      diagnostic: [
        '2026-09-26T08:14:02Z INFO worker started component=' + topic.replaceAll(' ', '_'),
        '2026-09-26T08:14:03Z INFO smoke suite completed checks=12',
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
  const noise = Array.from({ length: 150 }, (_, i) =>
    'INFO regression-' + String(i + 1).padStart(3, '0') + ': ' + topic
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

const configMergeCases: GeneralCase[] = [
  { name: 'empty', args: [{}, []], expected: {}, preserveArgs: true },
  { name: 'top-level-add', args: [{ host: 'db' }, [{ port: 5432 }]], expected: { host: 'db', port: 5432 } },
  { name: 'nested-merge', args: [{ service: { host: 'a', port: 80 } }, [{ service: { port: 443, tls: true } }]], expected: { service: { host: 'a', port: 443, tls: true } } },
  { name: 'later-overlay-wins', args: [{ retries: 1 }, [{ retries: 2 }, { retries: 3 }]], expected: { retries: 3 } },
  { name: 'list-replaces', args: [{ zones: ['eu', 'us'] }, [{ zones: ['ap'] }]], expected: { zones: ['ap'] } },
  { name: 'null-deletes', args: [{ host: 'db', port: 5432 }, [{ port: null }]], expected: { host: 'db' } },
  { name: 'nested-null-deletes', args: [{ tls: { cert: 'a', key: 'b' } }, [{ tls: { key: null } }]], expected: { tls: { cert: 'a' } } },
  { name: 'new-nested-copy', args: [{}, [{ limits: { burst: 4, rate: 2 } }]], expected: { limits: { burst: 4, rate: 2 } }, mutateInputAfter: { path: [1, 0, 'limits', 'burst'], value: 99 } },
  { name: 'scalar-to-map', args: [{ cache: false }, [{ cache: { ttl: 60 } }]], expected: { cache: { ttl: 60 } } },
  { name: 'map-to-scalar', args: [{ cache: { ttl: 60 } }, [{ cache: false }]], expected: { cache: false } },
  { name: 'deep-three-levels', args: [{ a: { b: { c: 1, d: 2 } } }, [{ a: { b: { c: 9 } } }]], expected: { a: { b: { c: 9, d: 2 } } }, mutateInputAfter: { path: [0, 'a', 'b', 'd'], value: 77 } },
  { name: 'delete-whole-nested', args: [{ a: { b: 1 }, x: 2 }, [{ a: null }]], expected: { x: 2 } },
  { name: 'null-base-preserved', args: [{ value: null }, [{}]], expected: { value: null } },
  { name: 'empty-overlay', args: [{ a: { b: 1 } }, [{}, {}]], expected: { a: { b: 1 } } },
  { name: 'input-not-mutated', args: [{ a: { b: 1 }, list: [1, 2] }, [{ a: { c: 2 }, list: [3] }]], expected: { a: { b: 1, c: 2 }, list: [3] }, preserveArgs: true },
  { name: 'overlay-order', args: [{ a: 0 }, [{ b: 1, a: 1 }, { c: 2, a: 2 }]], expected: { a: 2, b: 1, c: 2 } },
  { name: 'nested-list-copy', args: [{ a: { list: [1] } }, [{ a: { list: [2, 3] } }]], expected: { a: { list: [2, 3] } }, preserveArgs: true },
];

const headerRedactionCases: GeneralCase[] = [
  { name: 'empty', args: [[]], expected: [] },
  { name: 'ordinary-kept', args: [[['Accept', 'application/json'], ['X-Trace', 'abc']]], expected: [['Accept', 'application/json'], ['X-Trace', 'abc']] },
  { name: 'authorization-default', args: [[['Authorization', 'Bearer abc']]], expected: [['Authorization', '[REDACTED]']] },
  { name: 'authorization-case', args: [[['aUtHoRiZaTiOn', 'secret']]], expected: [['aUtHoRiZaTiOn', '[REDACTED]']] },
  { name: 'cookie-default', args: [[['Cookie', 'sid=123']]], expected: [['Cookie', '[REDACTED]']] },
  { name: 'set-cookie-default', args: [[['Set-Cookie', 'sid=123']]], expected: [['Set-Cookie', '[REDACTED]']] },
  { name: 'proxy-authorization', args: [[['Proxy-Authorization', 'Basic x']]], expected: [['Proxy-Authorization', '[REDACTED]']] },
  { name: 'api-key-default', args: [[['X-API-Key', 'k']]], expected: [['X-API-Key', '[REDACTED]']] },
  { name: 'extra-sensitive', args: [[['X-Trace', 'abc'], ['X-Id', '42']], ['x-trace']], expected: [['X-Trace', '[REDACTED]'], ['X-Id', '42']] },
  { name: 'extra-trimmed-casefolded', args: [[['X-Token', 'abc']], ['  x-ToKeN  ']], expected: [['X-Token', '[REDACTED]']] },
  { name: 'duplicates-preserved', args: [[['X-A', '1'], ['Authorization', 'a'], ['X-A', '2'], ['authorization', 'b']]], expected: [['X-A', '1'], ['Authorization', '[REDACTED]'], ['X-A', '2'], ['authorization', '[REDACTED]']] },
  { name: 'empty-sensitive', args: [[['Cookie', 'x'], ['X', 'y']], []], expected: [['Cookie', '[REDACTED]'], ['X', 'y']] },
  { name: 'blank-header-name-not-special', args: [[['', 'value'], [' Authorization ', 'value2']]], expected: [['', 'value'], [' Authorization ', '[REDACTED]']] },
  { name: 'values-untouched', args: [[['X-Data', '  spaced  '], ['X-Empty', '']]], expected: [['X-Data', '  spaced  '], ['X-Empty', '']] },
  { name: 'input-not-mutated', args: [[['Cookie', 'x'], ['X', 'y']], ['x']], expected: [['Cookie', '[REDACTED]'], ['X', '[REDACTED]']], preserveArgs: true },
];

const rateWindowCases: GeneralCase[] = [
  { name: 'empty', args: [[], 2, 1000], expected: [] },
  { name: 'under-limit', args: [[0, 100, 200], 3, 1000], expected: [true, true, true] },
  { name: 'limit', args: [[0, 100, 200], 2, 1000], expected: [true, true, false] },
  { name: 'rejected-does-not-consume', args: [[0, 1, 2, 1001], 1, 1000], expected: [true, false, false, true] },
  { name: 'boundary-is-in-window', args: [[0, 100], 1, 100], expected: [true, false] },
  { name: 'just-outside-window', args: [[0, 101], 1, 100], expected: [true, true] },
  { name: 'same-timestamp', args: [[5, 5, 5], 2, 10], expected: [true, true, false] },
  { name: 'multiple-expiry', args: [[0, 10, 20, 101, 102], 2, 100], expected: [true, true, false, true, false] },
  { name: 'large-limit', args: [[0, 1, 2], 99, 1], expected: [true, true, true] },
  { name: 'zero-time', args: [[0, 0], 1, 1], expected: [true, false] },
  { name: 'negative-timestamp', args: [[-1], 1, 100], raises: 'ValueError' },
  { name: 'decreasing', args: [[10, 9], 1, 100], raises: 'ValueError' },
  { name: 'zero-limit', args: [[0], 0, 100], raises: 'ValueError' },
  { name: 'zero-window', args: [[0], 1, 0], raises: 'ValueError' },
  { name: 'bool-limit', args: [[0], true, 100], raises: 'ValueError' },
  { name: 'float-timestamp', args: [[0.5], 1, 100], raises: 'ValueError' },
  { name: 'string-timestamp', args: [['0'], 1, 100], raises: 'ValueError' },
  { name: 'input-not-mutated', args: [[0, 1, 101], 2, 100], expected: [true, true, true], preserveArgs: true },
];

const paginationCases: GeneralCase[] = [
  { name: 'empty', args: [[], null, 2], expected: { items: [], next_after: null } },
  { name: 'defaults', args: [[{ id: 'a' }, { id: 'b' }]], expected: { items: [{ id: 'a' }, { id: 'b' }], next_after: null } },
  { name: 'first-page', args: [[{ id: 'a', v: 1 }, { id: 'b', v: 2 }, { id: 'c', v: 3 }], null, 2], expected: { items: [{ id: 'a', v: 1 }, { id: 'b', v: 2 }], next_after: 'b' } },
  { name: 'after-middle', args: [[{ id: 'a' }, { id: 'b' }, { id: 'c' }], 'b', 2], expected: { items: [{ id: 'c' }], next_after: null } },
  { name: 'after-first-limit-one', args: [[{ id: 'a' }, { id: 'b' }, { id: 'c' }], 'a', 1], expected: { items: [{ id: 'b' }], next_after: 'b' } },
  { name: 'after-last', args: [[{ id: 'a' }, { id: 'b' }], 'b', 2], expected: { items: [], next_after: null } },
  { name: 'large-limit', args: [[{ id: 'a' }, { id: 'b' }], null, 100], expected: { items: [{ id: 'a' }, { id: 'b' }], next_after: null } },
  { name: 'record-fields-preserved', args: [[{ id: 'a', nested: { x: 1 }, tags: ['x'] }], null, 2], expected: { items: [{ id: 'a', nested: { x: 1 }, tags: ['x'] }], next_after: null }, preserveArgs: true },
  { name: 'unknown-cursor', args: [[{ id: 'a' }], 'z', 2], raises: 'ValueError' },
  { name: 'duplicate-id', args: [[{ id: 'a' }, { id: 'a' }], null, 2], raises: 'ValueError' },
  { name: 'missing-id', args: [[{ v: 1 }], null, 2], raises: 'ValueError' },
  { name: 'empty-id', args: [[{ id: '' }], null, 2], raises: 'ValueError' },
  { name: 'non-string-id', args: [[{ id: 1 }], null, 2], raises: 'ValueError' },
  { name: 'zero-limit', args: [[{ id: 'a' }], null, 0], raises: 'ValueError' },
  { name: 'negative-limit', args: [[{ id: 'a' }], null, -1], raises: 'ValueError' },
  { name: 'limit-too-large', args: [[{ id: 'a' }], null, 101], raises: 'ValueError' },
  { name: 'bool-limit', args: [[{ id: 'a' }], null, true], raises: 'ValueError' },
  { name: 'invalid-after-type', args: [[{ id: 'a' }], 1, 2], raises: 'ValueError' },
];

const durationCases: GeneralCase[] = [
  { name: 'zero', args: ['0s'], expected: 0 },
  { name: 'seconds', args: ['2s'], expected: 2000 },
  { name: 'milliseconds', args: ['500ms'], expected: 500 },
  { name: 'minutes', args: ['2m'], expected: 120000 },
  { name: 'hours', args: ['1h'], expected: 3600000 },
  { name: 'days', args: ['1d'], expected: 86400000 },
  { name: 'compound-no-space', args: ['1h30m'], expected: 5400000 },
  { name: 'compound-space', args: [' 1h 30m 500ms '], expected: 5400500 },
  { name: 'decimal', args: ['1.5s'], expected: 1500 },
  { name: 'leading-dot', args: ['.25m'], expected: 15000 },
  { name: 'ceil-fraction', args: ['0.0001s'], expected: 1 },
  { name: 'mixed-units', args: ['2d 3h 4m 5s 6ms'], expected: 183845006 },
  { name: 'empty', args: [''], raises: 'ValueError' },
  { name: 'whitespace-only', args: ['   '], raises: 'ValueError' },
  { name: 'missing-unit', args: ['10'], raises: 'ValueError' },
  { name: 'space-inside-term', args: ['1 s'], raises: 'ValueError' },
  { name: 'negative', args: ['-1s'], raises: 'ValueError' },
  { name: 'unknown-unit', args: ['1w'], raises: 'ValueError' },
  { name: 'uppercase-unit', args: ['1S'], raises: 'ValueError' },
  { name: 'trailing-dot', args: ['1.s'], raises: 'ValueError' },
  { name: 'input-type', args: [1000], raises: 'ValueError' },
];

const dotenvCases: GeneralCase[] = [
  { name: 'empty', args: [''], expected: {} },
  { name: 'simple', args: ['HOST=db\nPORT=5432\n'], expected: { HOST: 'db', PORT: '5432' } },
  { name: 'spaces-around-equals', args: [' HOST = db \n'], expected: { HOST: 'db' } },
  { name: 'export-prefix', args: ['export API_KEY=abc\n'], expected: { API_KEY: 'abc' } },
  { name: 'comments-and-blanks', args: ['\n  # comment\nA=1\n\t# other\nB=2\n'], expected: { A: '1', B: '2' } },
  { name: 'inline-comment', args: ['A=value # explanation\n'], expected: { A: 'value' } },
  { name: 'hash-in-word', args: ['A=abc#123\n'], expected: { A: 'abc#123' } },
  { name: 'single-quote', args: ["A='  spaced # value  '\n"], expected: { A: '  spaced # value  ' } },
  { name: 'double-quote', args: ['A=\"hello world\"\n'], expected: { A: 'hello world' } },
  { name: 'double-escapes', args: ['A=\"line\\nnext\\t\\\"q\\\"\"\n'], expected: { A: 'line\nnext\t\"q\"' } },
  { name: 'quoted-hash', args: ['A=\"value # stays\" # comment\n'], expected: { A: 'value # stays' } },
  { name: 'empty-value', args: ["A=\nB=\"\"\nC=''\n"], expected: { A: '', B: '', C: '' } },
  { name: 'duplicate-last-wins', args: ['A=one\nA=two\n'], expected: { A: 'two' } },
  { name: 'defaults', args: ['PORT=8080\n', { HOST: 'localhost', PORT: '3000' }], expected: { HOST: 'localhost', PORT: '8080' }, preserveArgs: true },
  { name: 'preserve-default-order', args: ['B=2\n', { A: '1', B: 'old' }], expected: { A: '1', B: '2' } },
  { name: 'invalid-no-equals', args: ['A\n'], raises: 'ValueError' },
  { name: 'invalid-key', args: ['1A=x\n'], raises: 'ValueError' },
  { name: 'invalid-key-dash', args: ['A-B=x\n'], raises: 'ValueError' },
  { name: 'unterminated-single', args: ["A='x\n"], raises: 'ValueError' },
  { name: 'unterminated-double', args: ['A=\"x\n'], raises: 'ValueError' },
  { name: 'junk-after-quote', args: ['A=\"x\"junk\n'], raises: 'ValueError' },
  { name: 'non-string-defaults', args: ['A=1\n', []], raises: 'ValueError' },
];

const sortRecordCases: GeneralCase[] = [
  { name: 'empty', args: [[], ['name']], expected: [] },
  { name: 'ascending', args: [[{ name: 'b' }, { name: 'a' }], ['name']], expected: [{ name: 'a' }, { name: 'b' }] },
  { name: 'descending', args: [[{ score: 2 }, { score: 9 }, { score: 4 }], ['-score']], expected: [{ score: 9 }, { score: 4 }, { score: 2 }] },
  { name: 'multi-key', args: [[{group: 'b', score: 1}, {group: 'a', score: 2}, {group: 'a', score: 1}], ['group', '-score']], expected: [{group: 'a', score: 2}, {group: 'a', score: 1}, {group: 'b', score: 1}] },
  { name: 'stable-tie', args: [[{k: 1, id: 'first'}, {k: 1, id: 'second'}, {k: 0, id: 'third'}], ['k']], expected: [{k: 0, id: 'third'}, {k: 1, id: 'first'}, {k: 1, id: 'second'}] },
  { name: 'missing-last-ascending', args: [[{v: 2, id: 'a'}, {id: 'missing'}, {v: 1, id: 'b'}], ['v']], expected: [{v: 1, id: 'b'}, {v: 2, id: 'a'}, {id: 'missing'}] },
  { name: 'missing-last-descending', args: [[{v: 2, id: 'a'}, {id: 'missing'}, {v: 1, id: 'b'}], ['-v']], expected: [{v: 2, id: 'a'}, {v: 1, id: 'b'}, {id: 'missing'}] },
  { name: 'none-last', args: [[{v: null, id: 'none'}, {v: 1, id: 'one'}, {v: 2, id: 'two'}], ['v']], expected: [{v: 1, id: 'one'}, {v: 2, id: 'two'}, {v: null, id: 'none'}] },
  { name: 'negative-numbers', args: [[{v: -1}, {v: -3}, {v: 0}], ['v']], expected: [{v: -3}, {v: -1}, {v: 0}] },
  { name: 'key-with-leading-dash', args: [[{'-name': 'a'}, {'-name': 'b'}], ['--name']], expected: [{'-name': 'a'}, {'-name': 'b'}] },
  { name: 'rows-not-mutated', args: [[{v: 2}, {v: 1}], ['v']], expected: [{v: 1}, {v: 2}], preserveArgs: true },
  { name: 'empty-keys', args: [[{v: 1}], []], raises: 'ValueError' },
  { name: 'non-string-key', args: [[{v: 1}], [1]], raises: 'ValueError' },
  { name: 'empty-key-name', args: [[{v: 1}], ['']], raises: 'ValueError' },
  { name: 'only-minus', args: [[{v: 1}], ['-']], raises: 'ValueError' },
  { name: 'mixed-value-types', args: [[{v: 1}, {v: '1'}], ['v']], raises: 'ValueError' },
  { name: 'nested-values-not-supported', args: [[{v: {x: 1}}], ['v']], raises: 'ValueError' },
];

const urlCases: GeneralCase[] = [
  { name: 'simple', args: ['HTTP://Example.COM/path'], expected: 'http://example.com/path' },
  { name: 'root', args: ['https://Example.com'], expected: 'https://example.com/' },
  { name: 'default-http-port', args: ['http://example.com:80/a'], expected: 'http://example.com/a' },
  { name: 'default-https-port', args: ['https://example.com:443/a'], expected: 'https://example.com/a' },
  { name: 'nondefault-port', args: ['http://EXAMPLE.com:8080/a'], expected: 'http://example.com:8080/a' },
  { name: 'dot-segments', args: ['https://example.com/a/./b/../c/'], expected: 'https://example.com/a/c/' },
  { name: 'duplicate-slashes', args: ['https://example.com//a///b'], expected: 'https://example.com/a/b' },
  { name: 'query-sorted', args: ['https://example.com/p?z=2&a=1&z=1'], expected: 'https://example.com/p?a=1&z=1&z=2' },
  { name: 'query-blank', args: ['https://example.com/p?b=&a=hello%20world'], expected: 'https://example.com/p?a=hello+world&b=' },
  { name: 'query-duplicate-key-values', args: ['https://example.com/p?a=2&a=1'], expected: 'https://example.com/p?a=1&a=2' },
  { name: 'fragment-rejected', args: ['https://example.com/a#frag'], raises: 'ValueError' },
  { name: 'credentials-rejected', args: ['https://user:pass@example.com/a'], raises: 'ValueError' },
  { name: 'relative-rejected', args: ['/a/b'], raises: 'ValueError' },
  { name: 'scheme-rejected', args: ['ftp://example.com/a'], raises: 'ValueError' },
  { name: 'missing-host', args: ['https:///a'], raises: 'ValueError' },
  { name: 'invalid-port', args: ['http://example.com:abc/a'], raises: 'ValueError' },
  { name: 'trailing-dot-host', args: ['https://Example.COM./a'], expected: 'https://example.com/a' },
  { name: 'unicode-path', args: ['https://example.com/資料/é'], expected: 'https://example.com/資料/é' },
  { name: 'control-character', args: ['https://example.com/a\n'], raises: 'ValueError' },
];

function makeTask(
  id: string,
  objective: string,
  initial: string,
  requirements: string,
  source: string,
  functionName: string,
  cases: GeneralCase[],
  failure: string,
  topic: string,
  options: {
    stratum?: 'short' | 'long';
    files?: Readonly<Record<string, string>>;
    referenceFile?: string;
  } = {},
): GeneralCodingTask {
  const taskFixture = fixture(failure, topic, options.stratum ?? 'long');
  let item!: GeneralCodingTask;
  item = {
    id,
    objective,
    initial,
    requirements,
    source,
    functionName,
    cases: cases.map(test => caseWithFunction(functionName, test)),
    files: {
      'solver.py': source,
      'requirements.txt': requirements,
      'diagnostic.log': taskFixture.diagnostic,
      'aside.txt': taskFixture.aside,
      ...options.files,
    },
    turns: turnsFor(functionName, options.referenceFile),
    fixture: taskFixture,
    evaluate: workspace => evaluateGeneralTask(item, workspace),
  };
  return item;
}

const dotenvProjectGuide = [
  '# Runtime configuration loader',
  '',
  'The worker process receives configuration from a checked-in defaults file and an optional local environment file.',
  'The loader runs before logging starts, so parse failures must be reported as ordinary ValueError instances.',
  'Callers use the returned mapping to construct immutable service settings.',
  '',
  '## Ownership',
  '',
  'config_loader.py owns syntax parsing.',
  'startup.py owns precedence between defaults, environment variables, and command-line flags.',
  'The deployment wrapper owns file discovery and does not interpret values.',
  '',
  '## File conventions',
  '',
  'Configuration files use UTF-8 text and one assignment per physical line.',
  'Blank lines and comments are common because operators annotate emergency changes.',
  'The optional export spelling is accepted for compatibility with shell snippets.',
  'Keys are passed to the process environment exactly as parsed.',
  '',
  '## Error handling',
  '',
  'A malformed line should identify the file and line number at the caller boundary.',
  'The parser itself raises ValueError without printing or logging.',
  'Partial results must never escape after a malformed line.',
  'A caller may retry with a corrected file in the same process.',
  '',
  '## Review notes',
  '',
  'Keep the parser independent of the operating system environment.',
  'Do not call os.environ or read files from inside the parser.',
  'Do not mutate the defaults mapping supplied by a caller.',
  'Values are strings at this layer; numeric conversion belongs to schema validation.',
  'The startup path treats repeated definitions as deliberate operator overrides.',
  '',
  '## Compatibility',
  '',
  'The service still supports Python 3.11 and later.',
  'Only the standard library is available in the minimal worker image.',
  'Tests invoke the parser directly with text fixtures.',
  'The implementation should remain deterministic across locales and host platforms.',
  '',
  'This guide describes module boundaries and operational context; the function contract remains the authority for syntax details.',
].join('\n');

const urlProjectGuide = [
  '# HTTP cache key notes',
  '',
  'The client cache stores GET responses by a canonical URL string.',
  'The cache is shared by the request layer and the offline replay tool.',
  'A key must identify the same origin and resource for every supported spelling.',
  '',
  '## Request flow',
  '',
  'request.py parses a URL, applies the transport policy, and asks cache.py for a key.',
  'The transport layer rejects credentials before opening a socket.',
  'Redirect handling is outside this helper and supplies a fresh URL on every hop.',
  'Fragments are browser-only state and are never sent to the HTTP server.',
  '',
  '## Authority conventions',
  '',
  'The supported schemes are HTTP and HTTPS.',
  'Host names are case-insensitive and service records occasionally include a terminal dot.',
  'Default ports are omitted from cache keys so equivalent configuration does not fork entries.',
  'Non-default ports remain part of the authority.',
  '',
  '## Path conventions',
  '',
  'The origin server treats repeated separators and dot segments as equivalent resource paths.',
  'The canonical form always begins with a slash.',
  'A trailing slash can distinguish a collection endpoint from its parent resource.',
  'Unicode path text is retained for diagnostics and is encoded by the transport boundary later.',
  '',
  '## Query conventions',
  '',
  'Query order has no semantic meaning for this API.',
  'Blank values are meaningful because feature flags use a key with an empty value.',
  'Repeated keys are allowed and sorted by their key and value pair.',
  'Form encoding is used for the canonical query representation.',
  '',
  '## Safety and testing',
  '',
  'Credentials, fragments, malformed ports, and unsupported schemes must fail before caching.',
  'Do not perform DNS lookups or network I/O while building a key.',
  'The helper has no global cache and must return the same value for the same input.',
  'The implementation is used by both synchronous and asynchronous clients.',
  '',
  'This guide gives repository context; the function contract defines the exact normalization boundary.',
].join('\n');

export const generalTasks: readonly GeneralCodingTask[] = [
  makeTask(
    'config-merge',
    'Repair deep configuration overlay merging with deletion and copy semantics.',
    'Implement merge_settings(base, overlays) in solver.py. Read the contract before editing and keep the function free of side effects.',
    String.raw`Implement merge_settings(base, overlays).

base is a JSON-style dictionary and overlays is a list of dictionaries applied from left to right. Return a fresh dictionary. When both the current value and an overlay value are dictionaries, merge them recursively. Otherwise the overlay replaces the current value. Lists and scalar values replace rather than merge, and all nested values must be copied so later caller mutations cannot change the result. An overlay value of None deletes that key; deleting a missing key is harmless. A None already present in base remains when no overlay deletes it. Do not mutate base, overlays, or any nested list/dictionary. Inputs are dictionaries/lists containing JSON-style values.`,
    String.raw`def merge_settings(base, overlays):
    result = dict(base)
    for overlay in overlays:
        result.update(overlay)
    return result
`,
    'merge_settings',
    configMergeCases,
    'nested service settings were lost during overlay; original nested map was replaced by a shallow update',
    'configuration overlay',
  ),
  makeTask(
    'header-redaction',
    'Repair case-insensitive HTTP header redaction while preserving order, names, and duplicates.',
    'Implement redact_headers(headers, sensitive=()) in solver.py. Read the contract before editing.',
    String.raw`Implement redact_headers(headers, sensitive=()). headers is a list of two-item [name, value] lists. Return a new list of two-item lists in exactly the original order; never mutate the input. Preserve each header name and every non-sensitive value byte-for-byte. Header names are compared after ASCII whitespace trimming and case folding. By default redact the names authorization, proxy-authorization, cookie, set-cookie, and x-api-key. Also redact every name in the optional sensitive sequence using the same comparison. A redacted value is exactly the string [REDACTED]. Valid header names and values are strings.`,
    String.raw`DEFAULT_SENSITIVE = {'authorization', 'cookie'}

def redact_headers(headers, sensitive=()):
    return [[name, '[REDACTED]' if name in DEFAULT_SENSITIVE or name in sensitive else value]
            for name, value in headers]
`,
    'redact_headers',
    headerRedactionCases,
    'authorization and cookie values were emitted verbatim when header casing differed',
    'HTTP header',
    { stratum: 'short' },
  ),
  makeTask(
    'rate-window',
    'Repair sliding-window request admission with boundary expiry, rejection handling, and validation.',
    'Implement admit_requests(timestamps, limit, window_ms) in solver.py. Read the contract before editing.',
    String.raw`Implement admit_requests(timestamps, limit, window_ms). timestamps is a list of nonnegative integers in nondecreasing chronological order. limit and window_ms are positive integers; booleans are not integers for validation. Reject malformed values, negative timestamps, and decreasing timestamps with ValueError. For each request, return a bool indicating whether it is admitted. Keep accepted request timestamps in a sliding window. At timestamp t, an accepted request remains active when its timestamp is >= t - window_ms; requests strictly older than that are expired. Admit when fewer than limit accepted requests are active. Rejected requests do not consume capacity. Return one bool per input timestamp and do not mutate the input.`,
    String.raw`def admit_requests(timestamps, limit, window_ms):
    return [i < limit for i, _ in enumerate(timestamps)]
`,
    'admit_requests',
    rateWindowCases,
    'the sliding window admitted a request at the inclusive expiry boundary and counted rejected requests',
    'request admission',
  ),
  makeTask(
    'pagination',
    'Repair stable cursor pagination with validation, exclusive cursors, and an explicit next cursor.',
    'Implement paginate_records(records, after=None, limit=20) in solver.py. Read the contract before editing.',
    String.raw`Implement paginate_records(records, after=None, limit=20). records is an ordered list of dictionaries. Every record must contain a unique nonempty string id; malformed records or duplicate ids raise ValueError. after is None for the first page or a string id already present in records; the cursor record itself is excluded, and an unknown or non-string cursor raises ValueError. limit must be an integer from 1 through 100; booleans are invalid. Return a new dictionary {"items": page, "next_after": cursor}. Items preserve source order and contain the original record values. next_after is the id of the last returned item when more records remain, otherwise None. An empty page after the final cursor has next_after None. Do not mutate records.`,
    String.raw`def paginate_records(records, after=None, limit=20):
    return {'items': records[:limit], 'next_after': records[limit - 1]['id'] if len(records) > limit else None}
`,
    'paginate_records',
    paginationCases,
    'cursor b returned the first page again and the next cursor was omitted at a page boundary',
    'API pagination',
  ),
  makeTask(
    'duration',
    'Repair configuration duration parsing across compound units, decimals, rounding, and malformed text.',
    'Implement parse_duration(text) in solver.py. Read the contract before editing.',
    String.raw`Implement parse_duration(text). text must be a string containing one or more duration terms. A term is a nonnegative decimal number followed immediately by one lowercase unit: ms, s, m, h, or d. A number may be an integer, digits followed by a decimal fraction, or a leading-dot fraction such as .25. Terms may be adjacent or separated by ASCII whitespace; surrounding whitespace is allowed, but whitespace inside a term is not. Convert the total to milliseconds (d=86400000, h=3600000, m=60000, s=1000, ms=1) and round upward to the next integer millisecond. Reject empty text, signs, missing/unknown/uppercase units, malformed decimals, non-string input, and any other characters with ValueError.`,
    String.raw`def parse_duration(text):
    return int(float(text.rstrip('s')) * 1000)
`,
    'parse_duration',
    durationCases,
    'compound duration 1h30m was truncated and malformed unit text was accepted',
    'configuration duration',
    { stratum: 'short' },
  ),
  makeTask(
    'dotenv',
    'Repair dotenv-style environment parsing with quoting, escapes, comments, defaults, and validation.',
    'Implement parse_env(text, defaults=None) in solver.py. Read the contract before editing.',
    String.raw`Implement parse_env(text, defaults=None). Return a new dictionary, starting with a copy of defaults when defaults is supplied; defaults must be a dictionary. Parse each physical line independently. Ignore blank lines and lines whose first non-whitespace character is #. An optional export followed by whitespace may preced a definition. A key matches [A-Za-z_][A-Za-z0-9_]*, with optional surrounding whitespace before =. For an unquoted value, trim surrounding whitespace; an inline # starts a comment only when it is at the beginning or preceded by whitespace, so abc#123 remains part of the value. A single-quoted value preserves every character until the next single quote and a double-quoted value processes only the escapes \\, \", \\n, \\r, \\t, and \\#. After a quoted value only whitespace and an optional comment are allowed. Empty values are valid. Duplicate keys use the last definition. Any nonempty malformed line, invalid key, unknown escape, unterminated quote, or junk after a quote raises ValueError.`,
    String.raw`def parse_env(text, defaults=None):
    result = {} if defaults is None else dict(defaults)
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result
`,
    'parse_env',
    dotenvCases,
    'quoted values and inline comments were parsed as part of the key/value text',
    'dotenv environment file',
    {
      stratum: 'short',
      referenceFile: 'project-guide.md',
      files: { 'project-guide.md': dotenvProjectGuide },
    },
  ),
  makeTask(
    'record-sort',
    'Repair stable multi-key record sorting with descending keys and predictable missing-value placement.',
    'Implement sort_records(records, keys) in solver.py. Read the contract before editing.',
    String.raw`Implement sort_records(records, keys). Return a new list of the input dictionaries in a stable order; do not mutate records or dictionaries. keys must be a nonempty list of nonempty strings. A key beginning with one '-' sorts descending; the rest sorts ascending. The field name after the optional '-' must be present as a name, so '-' alone is invalid. For each field, values are JSON scalars: strings, integers/floats, or None. None and a missing field both sort after every non-None value for that field, for both ascending and descending order, while retaining stable order among equal/missing rows. Non-None values for one field must have a common comparable type; mixed types or nested values raise ValueError. Preserve input order for complete ties.`,
    String.raw`def sort_records(records, keys):
    if not keys:
        return list(records)
    return sorted(records, key=lambda row: row.get(keys[0]))
`,
    'sort_records',
    sortRecordCases,
    'descending and missing fields were ordered inconsistently, and the first key alone controlled the result',
    'record export',
  ),
  makeTask(
    'canonical-url',
    'Repair canonical HTTP URL normalization with safe authority checks, path cleanup, and deterministic queries.',
    'Implement canonical_url(url) in solver.py. Read the contract before editing.',
    String.raw`Implement canonical_url(url). Accept only absolute http or https URLs. Lowercase the scheme and hostname, remove one trailing dot from the hostname, and reject credentials, fragments, missing hosts, invalid ports, control characters, and unsupported schemes with ValueError. Remove the default port 80 for http and 443 for https; preserve a valid non-default port. Normalize the path by removing dot segments, collapsing repeated slashes, retaining a leading slash, and retaining a trailing slash when the input path ended with one (the root path is /). Parse query pairs with blank values retained, sort pairs lexicographically by key then value, and encode them with standard application/x-www-form-urlencoded quoting; omit the ? when there are no pairs. Preserve Unicode path characters. Return the canonical URL string.`,
    String.raw`from urllib.parse import urlparse

def canonical_url(url):
    parsed = urlparse(url)
    return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()).geturl()
`,
    'canonical_url',
    urlCases,
    'URL query order and dot segments remained unstable, and credentials were accepted',
    'HTTP URL',
    {
      stratum: 'short',
      referenceFile: 'project-guide.md',
      files: { 'project-guide.md': urlProjectGuide },
    },
  ),
];

export const generalTaskById: ReadonlyMap<string, GeneralCodingTask> = new Map(
  generalTasks.map(item => [item.id, item]),
);

export function getGeneralTask(id: string): GeneralCodingTask {
  const found = generalTaskById.get(id);
  if (!found) throw new Error('Unknown general benchmark task: ' + id);
  return found;
}

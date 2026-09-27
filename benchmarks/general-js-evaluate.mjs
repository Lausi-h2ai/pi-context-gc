#!/usr/bin/env node
/*
 * Hidden evaluator for the optional Node general-coding catalog.
 *
 * The host process owns the case list and expected values.  Each candidate
 * call runs in a fresh child process and receives only the workspace, module
 * entry, export name, and that case's input arguments.  In particular, the
 * child never receives the case name or expected value.  Public npm tests run
 * in the host evaluator before hidden cases and are also isolated by cwd.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const WORKER_ENV = 'PI_GENERAL_JS_EVALUATOR_WORKER';
const MARKER = 'GENERAL_JS_EVALUATION_JSON=';
const MAX_OUTPUT = 4 * 1024 * 1024;
const BUILTIN_ERRORS = new Set([
  'Error', 'TypeError', 'RangeError', 'ReferenceError', 'SyntaxError',
  'EvalError', 'URIError', 'AggregateError',
]);

function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function strictEqual(actual, expected) {
  if (actual === null || expected === null) return actual === expected;
  if (typeof actual !== typeof expected) return false;
  if (Array.isArray(actual) || Array.isArray(expected)) {
    return Array.isArray(actual) && Array.isArray(expected)
      && actual.length === expected.length
      && actual.every((value, index) => strictEqual(value, expected[index]));
  }
  if (typeof actual === 'object') {
    const actualKeys = Object.keys(actual);
    const expectedKeys = Object.keys(expected);
    return actualKeys.length === expectedKeys.length
      && actualKeys.every((key) => Object.prototype.hasOwnProperty.call(expected, key)
        && strictEqual(actual[key], expected[key]));
  }
  return Object.is(actual, expected);
}

function safeJson(value) {
  try {
    return JSON.stringify(value);
  } catch (error) {
    return JSON.stringify({ protocolError: 'value is not JSON serialisable: ' + String(error) });
  }
}

function setPath(root, path, value) {
  if (!Array.isArray(path) || path.length === 0) throw new Error('empty mutation path');
  let target = root;
  for (const component of path.slice(0, -1)) target = target[component];
  target[path[path.length - 1]] = clone(value);
}

function normaliseEntry(workspace, entry) {
  if (typeof workspace !== 'string' || typeof entry !== 'string' || isAbsolute(entry)) {
    throw new Error('entry must be a relative path');
  }
  const root = resolve(workspace);
  const candidate = resolve(root, entry);
  const outside = relative(root, candidate).startsWith('..');
  if (outside || !existsSync(candidate)) throw new Error('entry is outside workspace or missing');
  return candidate;
}

function captureCandidateStdout() {
  const originalWrite = process.stdout.write.bind(process.stdout);
  let output = '';
  process.stdout.write = (chunk, encoding, callback) => {
    const text = Buffer.isBuffer(chunk) ? chunk.toString() : String(chunk);
    output += text;
    if (typeof encoding === 'function') encoding();
    else if (typeof callback === 'function') callback();
    return true;
  };
  return {
    get value() { return output; },
    restore() { process.stdout.write = originalWrite; },
  };
}

async function workerMain() {
  let captured;
  let request;
  try {
    request = JSON.parse(readFileSync(0, 'utf8'));
    const workspace = resolve(request.workspace);
    const entry = normaliseEntry(workspace, request.entry);
    const args = clone(request.args ?? []);
    const before = clone(args);
    captured = captureCandidateStdout();
    let actual;
    let candidateError;
    try {
      const module = await import(pathToFileURL(entry).href + '?candidate=' + String(Date.now()));
      const functionValue = module[request.exportName];
      if (typeof functionValue !== 'function') throw new TypeError('export is not a function: ' + request.exportName);
      actual = await functionValue(...args);
    } catch (error) {
      candidateError = error;
    }
    const argsAfterCall = clone(args);
    if (request.mutateInputAfter) setPath(args, request.mutateInputAfter.path, request.mutateInputAfter.value);
    const payload = candidateError
      ? {
        ok: false,
        errorName: candidateError?.constructor?.name ?? 'Error',
        errorBuiltin: BUILTIN_ERRORS.has(candidateError?.constructor?.name ?? '')
          && candidateError?.constructor === globalThis[candidateError?.constructor?.name],
        errorMessage: String(candidateError?.message ?? candidateError),
        argsBefore: before,
        argsAfter: argsAfterCall,
        capturedStdout: captured.value,
      }
      : {
        ok: true,
        value: actual,
        valueType: actual === null ? 'null' : typeof actual,
        argsBefore: before,
        argsAfter: argsAfterCall,
        capturedStdout: captured.value,
      };
    captured.restore();
    process.stdout.write(safeJson(payload) + '\n');
  } catch (error) {
    if (captured) captured.restore();
    process.stdout.write(safeJson({
      ok: false,
      protocolError: String(error?.message ?? error),
      errorName: error?.constructor?.name ?? 'Error',
      errorBuiltin: error?.constructor === Error,
      argsBefore: request?.args ?? [],
      argsAfter: request?.args ?? [],
      capturedStdout: captured?.value ?? '',
    }) + '\n');
  }
}

function runPublicTests(workspace, command) {
  if (!Array.isArray(command) || command.length === 0) {
    return { ok: true, status: 0, stdout: '', stderr: '' };
  }
  const [executable, ...argumentsList] = command;
  try {
    const result = spawnSync(executable, argumentsList, {
      cwd: workspace,
      encoding: 'utf8',
      timeout: 12_000,
      maxBuffer: MAX_OUTPUT,
      shell: false,
      env: {
        ...process.env,
        NODE_ENV: 'test',
        PI_GENERAL_JS_PUBLIC_TEST: '1',
      },
    });
    return {
      ok: result.status === 0 && !result.error,
      status: result.status,
      stdout: (result.stdout ?? '').slice(-20_000),
      stderr: (result.stderr ?? '').slice(-20_000),
      ...(result.error ? { error: String(result.error) } : {}),
    };
  } catch (error) {
    return { ok: false, status: null, error: String(error) };
  }
}

function expectedErrorMatches(worker, expectedName) {
  return !worker.ok
    && !worker.protocolError
    && worker.errorName === expectedName
    && worker.errorBuiltin === true;
}

function runCase(request, testCase, entry) {
  const before = clone(testCase.args ?? []);
  const workerRequest = {
    workspace: request.workspace,
    // Keep the catalog's relative entry in the child request.  The child
    // resolves and validates it against its workspace independently.
    entry: request.entry,
    exportName: request.exportName,
    args: before,
  };
  if (testCase.mutateInputAfter) workerRequest.mutateInputAfter = testCase.mutateInputAfter;
  const result = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--worker'], {
    cwd: request.workspace,
    input: JSON.stringify(workerRequest),
    encoding: 'utf8',
    timeout: 7_000,
    maxBuffer: MAX_OUTPUT,
    shell: false,
    env: { ...process.env, [WORKER_ENV]: '1' },
  });
  let worker;
  try {
    const lines = (result.stdout ?? '').trim().split('\n').filter(Boolean);
    if (result.status !== 0 || lines.length !== 1) throw new Error('worker protocol had unexpected output');
    worker = JSON.parse(lines[0]);
  } catch (error) {
    return {
      name: testCase.name,
      pass: false,
      error: String(error),
      stdout: (result.stdout ?? '').slice(-2000),
      stderr: (result.stderr ?? '').slice(-2000),
    };
  }

  let pass;
  if (testCase.throws) pass = expectedErrorMatches(worker, testCase.throws);
  else pass = worker.ok && strictEqual(worker.value, testCase.expected);
  if (!strictEqual(worker.argsAfter, worker.argsBefore)) pass = false;
  if (testCase.mutateInputAfter && worker.ok && !strictEqual(worker.value, testCase.expected)) pass = false;
  const output = { name: testCase.name, pass, capturedStdout: worker.capturedStdout ?? '' };
  if (worker.ok) output.actual = worker.value;
  else if (worker.errorName) output.error = { name: worker.errorName, message: worker.errorMessage };
  if (worker.protocolError) output.protocolError = worker.protocolError;
  if (!strictEqual(worker.argsAfter, worker.argsBefore)) output.mutation = { before: worker.argsBefore, after: worker.argsAfter };
  return output;
}

function evaluate(request) {
  if (!request || typeof request !== 'object') throw new Error('request must be an object');
  const workspace = resolve(request.workspace);
  const entry = normaliseEntry(workspace, request.entry);
  if (!Array.isArray(request.cases)) throw new Error('cases must be an array');
  const publicTests = runPublicTests(workspace, request.publicTestCommand);
  const cases = request.cases.map((testCase) => runCase({ ...request, workspace }, testCase, entry));
  const passed = cases.filter((testCase) => testCase.pass).length;
  return {
    passed,
    total: cases.length,
    success: publicTests.ok && passed === cases.length,
    publicTests,
    cases,
  };
}

async function hostMain() {
  try {
    const request = JSON.parse(readFileSync(0, 'utf8'));
    process.stdout.write(MARKER + JSON.stringify(evaluate(request)) + '\n');
  } catch (error) {
    process.stdout.write(MARKER + JSON.stringify({
      passed: 0,
      total: 0,
      success: false,
      publicTests: { ok: false, status: null, error: String(error?.message ?? error) },
      cases: [],
      error: String(error?.stack ?? error),
    }) + '\n');
    process.exitCode = 1;
  }
}

if (process.env[WORKER_ENV] === '1' || process.argv.includes('--worker')) await workerMain();
else await hostMain();

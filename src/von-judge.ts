import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import type { Judge, Verdict } from './judge.js';

/**
 * Von's public model identifier.  The worker also pins the Hub snapshot used
 * to obtain the weights; keeping the identifier here makes benchmark output
 * unambiguous when this adapter is selected alongside Laya.
 */
export const VON_MODEL_ID = 'von-1.2.0';
export const VON_BACKEND = 'von-1.2';
export const VON_HF_REPO = 'wfzyx/von';
export const VON_HF_REVISION = '5df8185a4f2327ad0a7cd117cc4f701ac557b9ae';

export interface VonJudgeOptions {
  /** Python interpreter containing the local von-sdk installation. */
  python?: string;
  /** JSONL worker.  This is injectable so the protocol can be tested offline. */
  worker?: string;
  /** Working directory used by the worker and for its local checkpoint lookup. */
  cwd?: string;
  /** Environment additions for the worker. */
  env?: NodeJS.ProcessEnv;
  /** Model label passed to Von. Defaults to the pinned public release. */
  model?: string;
  /** Von backend alias. Defaults to the 1.2 option-marker backend. */
  backend?: string;
  /** Optional local checkpoint directory. Avoids a Hub download when supplied. */
  checkpointDir?: string;
  /** Startup timeout, including an optional first weight download and warmup. */
  startupTimeoutMs?: number;
  /** Per-request inference timeout. */
  inferenceTimeoutMs?: number;
  /** Pipe worker diagnostics to the host stderr. */
  inheritStderr?: boolean;
}

interface PendingRequest {
  resolve: (value: Verdict) => void;
  reject: (reason: Error) => void;
  timer: NodeJS.Timeout;
}

const ACTIONS = new Set<Verdict['action']>(['KEEP_FULL', 'KEEP_RESULT', 'EXTERNALIZE', 'DISCARD']);

function finiteNumber(value: unknown, name: string, min = 0, max = Number.POSITIVE_INFINITY): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new Error(`Von returned invalid ${name}`);
  }
  return value;
}

function decodeVerdict(value: unknown, id: number): Verdict {
  if (!value || typeof value !== 'object') throw new Error('Von returned a non-object response');
  const response = value as Record<string, unknown>;
  if (response.id !== id) throw new Error(`Von returned an unexpected request id (${String(response.id)})`);
  if (typeof response.error === 'string' && response.error) throw new Error(`Von request failed: ${response.error}`);
  if (typeof response.action !== 'string' || !ACTIONS.has(response.action as Verdict['action'])) {
    throw new Error('Von returned an invalid action');
  }
  const discardProbability = finiteNumber(response.discardProbability, 'discardProbability', 0, 1);
  const durableProbability = finiteNumber(response.durableProbability, 'durableProbability', 0, 1);
  const windows = finiteNumber(response.windows, 'windows', 1);
  if (!Number.isInteger(windows)) throw new Error('Von returned a non-integer window count');
  const latencyMs = finiteNumber(response.latencyMs, 'latencyMs');
  return {
    action: response.action as Verdict['action'],
    discardProbability,
    durableProbability,
    windows,
    latencyMs,
    raw: response.raw,
  };
}

/**
 * Local Von judge using a persistent Python JSONL worker.
 *
 * The adapter deliberately rejects startup and inference failures.  The
 * context collector already treats a rejected judge call as a keep decision,
 * which is the fail-open behavior required for a retention system.
 */
export class VonJudge implements Judge {
  private readonly child: ChildProcessWithoutNullStreams;
  private readonly pending = new Map<number, PendingRequest>();
  private nextId = 0;
  private closed = false;
  private startupSettled = false;
  private startupTimer?: NodeJS.Timeout;
  readonly ready: Promise<Record<string, unknown>>;

  constructor(options: VonJudgeOptions = {}) {
    const root = fileURLToPath(new URL('../', import.meta.url));
    const model = options.model ?? process.env.VON_MODEL ?? VON_MODEL_ID;
    const backend = options.backend ?? process.env.VON_BACKEND ?? VON_BACKEND;
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      ...options.env,
      HF_HUB_DISABLE_TELEMETRY: '1',
      VON_MODEL: model,
      VON_BACKEND: backend,
      VON_HF_REPO: options.env?.VON_HF_REPO ?? process.env.VON_HF_REPO ?? VON_HF_REPO,
      VON_HF_REVISION: options.env?.VON_HF_REVISION ?? process.env.VON_HF_REVISION ?? VON_HF_REVISION,
    };
    if (options.checkpointDir) env.VON_CHECKPOINT_DIR = options.checkpointDir;
    // This adapter is intentionally local-only.  Clearing these variables
    // prevents an inherited shell configuration from switching the worker to
    // a hosted endpoint or from attaching credentials to model fetches.
    delete env.VON_BASE_URL;
    delete env.VON_API_KEY;
    delete env.TYPESAFE_API_KEY;
    delete env.HF_TOKEN;
    delete env.HUGGINGFACE_HUB_TOKEN;

    const python = options.python ?? process.env.VON_PYTHON ?? `${root}.venv/bin/python`;
    const worker = options.worker ?? process.env.VON_WORKER ?? `${root}python/von-judge.py`;
    const cwd = options.cwd ?? process.env.VON_CWD ?? root;
    this.child = spawn(python, [worker], { cwd, env });
    if (options.inheritStderr !== false) this.child.stderr.pipe(process.stderr);

    const startupTimeout = options.startupTimeoutMs ?? 600_000;
    const inferenceTimeout = options.inferenceTimeoutMs ?? 60_000;
    let resolveReady!: (value: Record<string, unknown>) => void;
    let rejectReady!: (reason: Error) => void;
    this.ready = new Promise<Record<string, unknown>>((resolve, reject) => {
      resolveReady = resolve;
      rejectReady = reject;
      this.startupTimer = setTimeout(() => {
        this.startupSettled = true;
        reject(new Error('Von startup timed out'));
        this.close();
      }, startupTimeout);
    });

    const failPending = (error: Error) => {
      for (const request of this.pending.values()) {
        clearTimeout(request.timer);
        request.reject(error);
      }
      this.pending.clear();
    };
    const failStartup = (error: Error) => {
      if (this.startupSettled) return;
      this.startupSettled = true;
      if (this.startupTimer) clearTimeout(this.startupTimer);
      rejectReady(error);
    };

    this.child.on('error', error => {
      const wrapped = new Error(`Von worker failed to start: ${error.message}`);
      failStartup(wrapped);
      failPending(wrapped);
    });
    this.child.on('exit', code => {
      const error = new Error(`Von worker exited (${code ?? 'signal'})`);
      failStartup(error);
      failPending(error);
    });
    createInterface({ input: this.child.stdout }).on('line', line => {
      let value: unknown;
      try { value = JSON.parse(line); } catch { return; }
      if (value && typeof value === 'object' && (value as Record<string, unknown>).ready === true) {
        if (!this.startupSettled) {
          this.startupSettled = true;
          if (this.startupTimer) clearTimeout(this.startupTimer);
          resolveReady(value as Record<string, unknown>);
        }
        return;
      }
      if (value && typeof value === 'object' && !this.startupSettled
        && typeof (value as Record<string, unknown>).error === 'string') {
        failStartup(new Error(`Von startup failed: ${(value as Record<string, unknown>).error}`));
        return;
      }
      const id = value && typeof value === 'object' ? (value as Record<string, unknown>).id : undefined;
      if (typeof id !== 'number') return;
      const request = this.pending.get(id);
      if (!request) return;
      this.pending.delete(id);
      clearTimeout(request.timer);
      try { request.resolve(decodeVerdict(value, id)); }
      catch (error) { request.reject(error instanceof Error ? error : new Error(String(error))); }
    });

    // Keep the timeout in scope for TypeScript's definite assignment analysis.
    void inferenceTimeout;
    this.inferenceTimeoutMs = inferenceTimeout;
  }

  private readonly inferenceTimeoutMs: number;

  async judge(task: string, tail: string): Promise<Verdict> {
    await this.ready;
    if (this.closed) throw new Error('Von judge is closed');
    const id = ++this.nextId;
    return new Promise<Verdict>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('Von inference timed out'));
      }, this.inferenceTimeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      try {
        this.child.stdin.write(JSON.stringify({ id, task, tail }) + '\n', error => {
          if (!error) return;
          clearTimeout(timer);
          this.pending.delete(id);
          reject(error);
        });
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error instanceof Error ? error : new Error(String(error)));
      }
    });
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    if (this.startupTimer) clearTimeout(this.startupTimer);
    const error = new Error('Von judge closed');
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(error);
    }
    this.pending.clear();
    this.child.kill();
  }
}

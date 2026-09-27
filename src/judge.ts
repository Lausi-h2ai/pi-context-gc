import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

export type Action = 'KEEP_FULL' | 'KEEP_RESULT' | 'EXTERNALIZE' | 'DISCARD';
export interface Verdict {
  action: Action; discardProbability: number; durableProbability: number;
  windows: number; latencyMs: number; raw?: unknown;
}
export interface Judge { judge(task: string, tail: string): Promise<Verdict> }

export class LayaJudge implements Judge {
  private child: ChildProcessWithoutNullStreams;
  private pending = new Map<number, { resolve: (v: Verdict) => void; reject: (e: Error) => void; timer: NodeJS.Timeout }>();
  private nextId = 0;
  readonly ready: Promise<Record<string, unknown>>;
  constructor() {
    const root = fileURLToPath(new URL('../', import.meta.url));
    this.child = spawn(process.env.LAYA_PYTHON ?? `${root}.venv/bin/python`, [`${root}python/judge.py`], { env: { ...process.env, HF_HUB_DISABLE_TELEMETRY: '1' } });
    this.child.stderr.pipe(process.stderr);
    this.ready = new Promise((resolve, reject) => {
      const timer = setTimeout(() => { reject(new Error('Laya startup timed out')); this.close(); }, 600_000);
      this.child.on('error', e => { clearTimeout(timer); reject(e); });
      this.child.on('exit', code => {
        clearTimeout(timer); reject(new Error(`Laya exited (${code})`));
        for (const p of this.pending.values()) { clearTimeout(p.timer); p.reject(new Error('Laya worker exited')); }
        this.pending.clear();
      });
      createInterface({ input: this.child.stdout }).on('line', line => {
        let value: any;
        try { value = JSON.parse(line); } catch { return; }
        if (value.ready) { clearTimeout(timer); resolve(value); return; }
        const p = this.pending.get(value.id);
        if (!p) return;
        this.pending.delete(value.id); clearTimeout(p.timer);
        if (value.error) p.reject(new Error(value.error)); else p.resolve(value);
      });
    });
  }
  async judge(task: string, tail: string): Promise<Verdict> {
    await this.ready;
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error('Laya inference timed out')); }, 60_000);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(JSON.stringify({ id, task, tail }) + '\n', error => {
        if (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
      });
    });
  }
  close() { this.child.kill(); }
}

import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import type { AgentSession, SessionEntry } from '@earendil-works/pi-coding-agent';
import type { Judge, Verdict } from './judge.js';

export interface Decision {
  action: 'KEEP' | 'DROP'; reason: string; checkpoint: string | null; leaf: string | null;
  verdict?: Verdict; beforeMessages: number; afterMessages: number; archive?: string;
}
export function choose(verdict: Verdict, protectedTail: boolean, threshold = 0.95): 'KEEP' | 'DROP' {
  if (protectedTail || !Number.isFinite(verdict.discardProbability) || !Number.isFinite(verdict.durableProbability)) return 'KEEP';
  return verdict.action === 'DISCARD' && verdict.discardProbability >= threshold && verdict.discardProbability <= 1
    && verdict.durableProbability >= 0 && verdict.durableProbability <= 1 - threshold ? 'DROP' : 'KEEP';
}
export function tailText(entries: SessionEntry[]): string {
  return entries.filter(e => e.type === 'message').map(e => {
    const m = e.message;
    return `${m.role}: ${'content' in m ? (typeof m.content === 'string' ? m.content : JSON.stringify(m.content)) : JSON.stringify(m)}`;
  }).join('\n');
}
export function protectedEntries(entries: SessionEntry[]): boolean {
  // Only known read-only tools may be forgotten. Shell/custom tools can mutate
  // external state even if they report failure. Never rewind across compaction.
  const readOnly = new Set(['read', 'grep', 'find', 'ls']);
  return entries.some(e => {
    if (['compaction', 'branch_summary', 'context_edit', 'model_change'].includes(e.type)) return true;
    if (e.type === 'custom_message') return true;
    if (e.type !== 'message') return false;
    const m = e.message;
    if ('content' in m && Array.isArray(m.content) && m.content.some(c => c.type === 'image')) return true;
    if (m.role === 'bashExecution') return true;
    if (m.role === 'toolResult') return m.isError || !readOnly.has(m.toolName);
    if (m.role === 'assistant') return m.stopReason === 'error' || m.stopReason === 'aborted'
      || m.content.some(c => c.type === 'toolCall' && !readOnly.has(c.name));
    return false;
  });
}

export class ContextGC {
  checkpoint: string | null;
  constructor(readonly session: AgentSession, readonly judge: Judge, public task: string,
              readonly logPath: string, readonly mode: 'auto' | 'shadow' = 'shadow', readonly threshold = 0.95) {
    this.checkpoint = session.sessionManager.getLeafId();
    const saved = [...session.sessionManager.getBranch()].reverse().find(e => e.type === 'custom' && e.customType === 'laya-gc-state');
    if (saved?.type === 'custom') {
      const state = saved.data as { checkpoint?: string | null; task?: string };
      if (state.task === task && state.checkpoint && session.sessionManager.getBranch().some(e => e.id === state.checkpoint)) this.checkpoint = state.checkpoint;
    }
    mkdirSync(dirname(logPath), { recursive: true });
  }
  private persist() {
    this.session.sessionManager.appendCustomEntry('laya-gc-state', { checkpoint: this.checkpoint, task: this.task });
  }
  promote() {
    if (this.session.isStreaming) throw new Error('Cannot checkpoint a streaming session');
    this.checkpoint = this.session.sessionManager.getLeafId();
    this.persist();
  }
  async collect(): Promise<Decision> {
    if (this.session.isStreaming) throw new Error('GC requires a settled session');
    const manager = this.session.sessionManager;
    const leaf = manager.getLeafId();
    const branch = manager.getBranch();
    const index = branch.findIndex(e => e.id === this.checkpoint);
    const entries = index >= 0 ? branch.slice(index + 1) : branch;
    const decision: Decision = { action: 'KEEP', reason: 'no checkpoint', checkpoint: this.checkpoint, leaf,
      beforeMessages: this.session.messages.length, afterMessages: this.session.messages.length };
    if (!entries.some(e => e.type === 'message' || e.type === 'custom_message')) { decision.reason = 'empty tail'; return decision; }
    const target = this.checkpoint ? manager.getEntry(this.checkpoint) : undefined;
    const unsafeTarget = target?.type === 'custom_message' || (target?.type === 'message' && target.message.role === 'user');
    if (this.checkpoint && index >= 0 && !unsafeTarget && !protectedEntries(entries)) {
      try {
        decision.verdict = await this.judge.judge(this.task, tailText(entries));
        decision.action = choose(decision.verdict, false, this.threshold);
        decision.reason = decision.action === 'DROP' ? 'confident disposable tail' : 'useful or uncertain tail';
      } catch (e) { decision.reason = `judge failed; retained: ${(e as Error).message}`; }
    } else if (unsafeTarget) decision.reason = 'user-message checkpoints navigate before the message; retained';
    else if (protectedEntries(entries)) decision.reason = 'side effects, errors, or context boundary';
    else if (this.checkpoint && index < 0) decision.reason = 'checkpoint is not an ancestor';
    // Recheck after inference: a host must not prune a newly changed branch.
    if (manager.getLeafId() !== leaf || this.session.isStreaming) {
      decision.action = 'KEEP'; decision.reason = 'session changed during judgment';
      this.checkpoint = null;
    } else if (decision.action === 'DROP' && this.mode === 'auto') {
      const archive = join(dirname(this.logPath), 'archive', `${manager.getSessionId()}-${leaf}.json`);
      mkdirSync(dirname(archive), { recursive: true });
      writeFileSync(archive, JSON.stringify({ checkpoint: this.checkpoint, leaf, entries }, null, 2));
      decision.archive = archive;
      const result = await this.session.navigateTree(this.checkpoint!, { summarize: false });
      if (result.cancelled) { decision.action = 'KEEP'; decision.reason = 'navigation cancelled'; this.promote(); }
      decision.afterMessages = this.session.messages.length;
      this.persist();
    } else {
      if (decision.action === 'DROP') decision.reason = 'shadow: would discard';
      this.promote();
    }
    appendFileSync(this.logPath, JSON.stringify({ time: new Date().toISOString(), sessionId: manager.getSessionId(), mode: this.mode, ...decision }) + '\n');
    return decision;
  }
  async restore(leaf: string) {
    const entry = this.session.sessionManager.getEntry(leaf);
    if (!entry) throw new Error('Unknown entry');
    if (entry.type === 'custom_message' || (entry.type === 'message' && entry.message.role === 'user')) throw new Error('Restore an assistant or metadata entry; Pi treats user entries as edit-before targets');
    const result = await this.session.navigateTree(leaf, { summarize: false });
    if (result.cancelled) throw new Error('Restore was cancelled');
    this.promote();
  }
}

/** Deterministic tool-log externalization; full output is kept on disk before replacement. */
export function externalize(text: string, directory: string, action: 'KEEP_RESULT' | 'EXTERNALIZE'): string {
  mkdirSync(directory, { recursive: true });
  const file = join(directory, `${createHash('sha256').update(text).digest('hex')}.txt`);
  writeFileSync(file, text);
  const lines = text.split('\n');
  const selected = action === 'KEEP_RESULT' ? lines.filter(l => /fail|error|passed|assert|expected|actual|summary/i.test(l)) : [];
  // Extraction is explicit; Laya classifies but never invents a summary.
  const excerpt = (selected.length ? selected.slice(-30) : lines.slice(-12)).join('\n').slice(-6000);
  return `[Full output: ${file}; ${text.length} characters. Excerpt follows.]\n${excerpt}`;
}

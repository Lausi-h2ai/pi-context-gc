import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import type { Judge, Verdict } from './judge.js';

export interface ContextPruneEvent {
  toolCallId: string;
  toolName: string;
  originalCharacters: number;
  retainedCharacters: number;
  action: Verdict['action'];
  discardProbability: number;
  durableProbability: number;
  archive: string;
}

/** A fixed, replayable budget policy. The judge orders old tool results by value. */
export function generalContextPolicy(options: {
  judge: Judge;
  task: () => string;
  archiveDirectory: string;
  observe?: (event: ContextPruneEvent) => void;
  retainedFraction?: number;
  minimumCharacters?: number;
  protectedReadBasenames?: readonly string[];
}): ExtensionFactory {
  const decisions = new Map<string, Verdict>();
  const observed = new Set<string>();
  const retainedFraction = options.retainedFraction ?? 0.70;
  const minimumCharacters = options.minimumCharacters ?? 600;
  const protectedReadBasenames = new Set(options.protectedReadBasenames ?? ['requirements.txt', 'project-guide.md', 'solver.py']);
  if (!(retainedFraction > 0 && retainedFraction <= 1)) throw new Error('retainedFraction must be in (0, 1]');
  return pi => {
    pi.on('context', async event => {
      const messages = event.messages;
      let lastUser = -1;
      for (let index = messages.length - 1; index >= 0; index--) {
        if (messages[index].role === 'user') { lastUser = index; break; }
      }
      if (lastUser < 0) return;
      const readPaths = new Map<string, string>();
      for (let index = 0; index < lastUser; index++) {
        const message = messages[index];
        if (message.role !== 'assistant') continue;
        for (const block of message.content) {
          if (block.type !== 'toolCall' || block.name !== 'read') continue;
          const path = block.arguments.path;
          if (typeof path === 'string') readPaths.set(block.id, path);
        }
      }
      const candidates: { index: number; key: string; text: string; verdict: Verdict; toolCallId: string; toolName: string }[] = [];
      for (let index = 0; index < lastUser; index++) {
        const message = messages[index];
        if (message.role !== 'toolResult' || message.isError || message.content.some(c => c.type !== 'text')) continue;
        const readPath = readPaths.get(message.toolCallId)?.replaceAll('\\', '/');
        if (readPath && protectedReadBasenames.has(readPath.split('/').at(-1) ?? '')) continue;
        const source = message.content.map(c => c.type === 'text' ? c.text : '').join('\n');
        if (source.length < minimumCharacters) continue;
        const key = `${message.toolCallId}:${createHash('sha256').update(source).digest('hex')}`;
        let verdict = decisions.get(key);
        if (!verdict) {
          try {
            verdict = await options.judge.judge(options.task(), `Earlier ${message.toolName} tool result:\n${source}`);
            decisions.set(key, verdict);
          } catch {
            // A failed classifier leaves the exact result in the model context.
            continue;
          }
        }
        candidates.push({ index, key, text: source, verdict, toolCallId: message.toolCallId, toolName: message.toolName });
      }
      if (!candidates.length) return;
      const allCharacters = messages.reduce((n, message) => n + JSON.stringify(message).length, 0);
      const savingsTarget = Math.max(0, allCharacters * (1 - retainedFraction));
      // Retain results that the classifier considers useful for exact continuation.
      const priority = { DISCARD: 0, EXTERNALIZE: 1, KEEP_RESULT: 2, KEEP_FULL: 3 };
      candidates.sort((a, b) => priority[a.verdict.action] - priority[b.verdict.action]
        || b.verdict.discardProbability - a.verdict.discardProbability || a.index - b.index);
      const replacements = new Map<number, string>();
      let removed = 0;
      for (const candidate of candidates) {
        if (removed >= savingsTarget) break;
        mkdirSync(options.archiveDirectory, { recursive: true });
        const archive = join(options.archiveDirectory, `${createHash('sha256').update(candidate.text).digest('hex')}.txt`);
        const replacement = `[Earlier ${candidate.toolName} output archived at ${archive}. Read it if exact details are needed.]`;
        if (candidate.text.length - replacement.length < minimumCharacters / 2) continue;
        writeFileSync(archive, candidate.text);
        replacements.set(candidate.index, replacement);
        removed += candidate.text.length - replacement.length;
        if (!observed.has(candidate.key)) {
          observed.add(candidate.key);
          options.observe?.({ toolCallId: candidate.toolCallId, toolName: candidate.toolName,
            originalCharacters: candidate.text.length, retainedCharacters: replacement.length,
            action: candidate.verdict.action, discardProbability: candidate.verdict.discardProbability,
            durableProbability: candidate.verdict.durableProbability, archive });
        }
      }
      if (!replacements.size) return;
      return { messages: messages.map((message, index) => {
        const replacement = replacements.get(index);
        return replacement && message.role === 'toolResult'
          ? { ...message, content: [{ type: 'text' as const, text: replacement }] }
          : message;
      }) };
    });
  };
}

import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import type { Judge, Verdict } from './judge.js';

export interface AggressiveFilterObservation {
  toolName: string; toolCallId: string; originalCharacters: number; retainedCharacters: number;
  changed: boolean; archive?: string; decisions: Pick<Verdict, 'action' | 'discardProbability' | 'durableProbability'>[];
  error?: string;
}

/** Split by whole lines so one useful failure cannot force a whole log to stay. */
export function splitOutput(text: string, limit = 1600): string[] {
  const chunks: string[] = [];
  let current = '';
  for (const line of text.match(/[^\n]*\n|[^\n]+$/g) ?? []) {
    if (current && current.length + line.length > limit) { chunks.push(current); current = ''; }
    if (line.length > limit) {
      if (current) { chunks.push(current); current = ''; }
      for (let offset = 0; offset < line.length; offset += limit) chunks.push(line.slice(offset, offset + limit));
    } else current += line;
  }
  if (current) chunks.push(current);
  return chunks;
}

export function aggressiveToolFilter(judge: Judge, getTask: () => string, directory: string,
                                     allowlist: string[], observe: (event: AggressiveFilterObservation) => void = () => {}): ExtensionFactory {
  return pi => {
    pi.on('tool_result', async event => {
      if (event.isError || !allowlist.includes(event.toolName) || event.content.some(c => c.type !== 'text')) return;
      const original = event.content.map(c => c.type === 'text' ? c.text : '').join('\n');
      if (original.length < 1000 || !/(?:^|\n)(?:PASSED|FAILED|ERROR|WARNING)\b/m.test(original)) return;
      const record: AggressiveFilterObservation = { toolName: event.toolName, toolCallId: event.toolCallId,
        originalCharacters: original.length, retainedCharacters: original.length, changed: false, decisions: [] };
      try {
        const chunks = splitOutput(original);
        const kept: string[] = [];
        let omitted = 0;
        for (const chunk of chunks) {
          const objective = `${getTask()} For diagnostic logs, keep actionable failures and discard routine passing status lines.`;
          const verdict = await judge.judge(objective, `Tool ${event.toolName} result chunk:\n${chunk}`);
          record.decisions.push({ action: verdict.action, discardProbability: verdict.discardProbability,
            durableProbability: verdict.durableProbability });
          if (verdict.action === 'KEEP_FULL') kept.push(chunk);
          else if (verdict.action === 'KEEP_RESULT') {
            const lines = chunk.split('\n').filter(line => /fail|error|assert|expected|actual|summary|warning/i.test(line));
            if (lines.length) {
              const excerpt = lines.join('\n') + '\n';
              kept.push(excerpt);
              if (excerpt.length < chunk.length) omitted++;
            } else omitted++;
          } else {
            // A classifier error must not hide the failure that prompted the read.
            const failures = chunk.split('\n').filter(line => /\b(?:FAILED|ERROR|AssertionError|expected|actual)\b/i.test(line));
            if (failures.length) kept.push(failures.join('\n') + '\n');
            omitted++;
          }
        }
        if (!omitted && kept.join('').length >= original.length) { observe(record); return; }
        mkdirSync(directory, { recursive: true });
        const archive = join(directory, `${createHash('sha256').update(original).digest('hex')}.txt`);
        writeFileSync(archive, original);
        const filtered = `[Full tool result archived at ${archive}; ${omitted} of ${chunks.length} chunks shortened or omitted. Read the archive if exact omitted details are needed.]\n${kept.join('')}`;
        if (filtered.length >= original.length) { observe(record); return; }
        record.archive = archive;
        record.retainedCharacters = filtered.length;
        record.changed = true;
        observe(record);
        return { content: [{ type: 'text', text: filtered }] };
      } catch (error) {
        record.error = String(error);
        observe(record);
      }
    });
  };
}

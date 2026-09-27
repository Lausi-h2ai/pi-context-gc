import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import { externalize } from './gc.js';
import type { Judge } from './judge.js';

/** Before-prompt filtering, opt-in for tools whose outputs are safe to excerpt.
 * Original output is archived. Source reads and shell mutations are never opted in implicitly. */
export interface FilterObservation {
  toolName: string; toolCallId: string; originalCharacters: number; retainedCharacters: number;
  action?: string; changed: boolean; error?: string;
}
export function toolFilter(judge: Judge, task: string, directory: string, allowlist: string[],
                           observe?: (event: FilterObservation) => void): ExtensionFactory {
  return pi => {
    pi.on('tool_result', async event => {
      if (event.isError || !allowlist.includes(event.toolName) || event.content.some(c => c.type !== 'text')) return;
      const text = event.content.map(c => c.type === 'text' ? c.text : '').join('\n');
      if (text.length < 4000) return;
      try {
        const verdict = await judge.judge(task, `Tool ${event.toolName}:\n${text}`);
        if (verdict.action === 'KEEP_RESULT' || verdict.action === 'EXTERNALIZE') {
          const excerpt = externalize(text, directory, verdict.action);
          observe?.({ toolName: event.toolName, toolCallId: event.toolCallId, originalCharacters: text.length,
            retainedCharacters: excerpt.length, action: verdict.action, changed: true });
          return { content: [{ type: 'text', text: excerpt }] };
        }
        observe?.({ toolName: event.toolName, toolCallId: event.toolCallId, originalCharacters: text.length,
          retainedCharacters: text.length, action: verdict.action, changed: false });
      } catch (error) {
        observe?.({ toolName: event.toolName, toolCallId: event.toolCallId, originalCharacters: text.length,
          retainedCharacters: text.length, changed: false, error: String(error) });
      }
    });
  };
}

import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import type { Judge, Verdict } from './judge.js';
import { choose, type ContextGC } from './gc.js';
import type { PostToolObservation } from './post-tool-gc.js';

/** Experimental policy: use a read-only result vote to collect a completed
 * turn if the whole-turn judge does not require full retention. */
export class AggressivePostToolGC {
  private pending = false;
  private eligible = true;
  private verdicts: Verdict[] = [];
  readonly extension: ExtensionFactory;

  constructor(judge: Judge, getTask: () => string, readonly threshold = 0.5,
              observe: (event: PostToolObservation) => void = () => {}) {
    this.extension = pi => {
      pi.on('tool_result', async event => {
        this.pending = true;
        if (event.isError || !['read', 'grep', 'find', 'ls'].includes(event.toolName)
          || event.content.some(c => c.type !== 'text')) { this.eligible = false; return; }
        const output = event.content.map(c => c.type === 'text' ? c.text : '').join('\n');
        try {
          const verdict = await judge.judge(getTask(), `Tool ${event.toolName}:\n${output}`);
          this.verdicts.push(verdict);
          observe({ toolName: event.toolName, toolCallId: event.toolCallId, verdict });
        } catch (error) {
          this.eligible = false;
          observe({ toolName: event.toolName, toolCallId: event.toolCallId, error: String(error) });
        }
      });
    };
  }

  async settle(gc: ContextGC) {
    if (!this.pending) return undefined;
    const hint = this.eligible && this.verdicts.length > 0
      && this.verdicts.every(v => choose(v, false, this.threshold) === 'DROP')
      ? { ...this.verdicts[0], discardProbability: Math.min(...this.verdicts.map(v => v.discardProbability)),
          durableProbability: Math.max(...this.verdicts.map(v => v.durableProbability)) } : undefined;
    this.pending = false;
    this.eligible = true;
    this.verdicts = [];
    return gc.collect(hint);
  }
}

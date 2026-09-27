import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import type { Judge, Verdict } from './judge.js';
import type { ContextGC } from './gc.js';

export interface PostToolObservation { toolName: string; toolCallId: string; verdict?: Verdict; error?: string }

/** Score at post-tool time; navigate only after the run is settled. Rejudge the
 * complete tail there so later discoveries or mutations cannot be lost based on
 * an earlier tool-only decision. Never break a live tool-call/result pair. */
export class PostToolGC {
  private pending = false;
  readonly extension: ExtensionFactory;
  constructor(judge: Judge, getTask: () => string, observe: (event: PostToolObservation) => void = () => {}) {
    this.extension = pi => {
      pi.on('tool_result', async event => {
        this.pending = true;
        if (event.isError || !['read', 'grep', 'find', 'ls'].includes(event.toolName)
          || event.content.some(c => c.type !== 'text')) return;
        const text = event.content.map(c => c.type === 'text' ? c.text : '').join('\n');
        try {
          const verdict = await judge.judge(getTask(), `Tool ${event.toolName}:\n${text}`);
          observe({ toolName: event.toolName, toolCallId: event.toolCallId, verdict });
        } catch (error) { observe({ toolName: event.toolName, toolCallId: event.toolCallId, error: String(error) }); }
      });
    };
  }
  async settle(gc: ContextGC) {
    if (!this.pending) return undefined;
    this.pending = false;
    return gc.collect();
  }
}

import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';
import { join } from 'node:path';
import { appendFileSync, mkdirSync } from 'node:fs';
import { LayaJudge } from './judge.js';
import { ContextGC } from './gc.js';
import { makeSession, subscriptionRuntime, prompt } from './runtime.js';
import { toolFilter } from './tool-filter.js';
import { PostToolGC } from './post-tool-gc.js';

const task = process.argv.find(a => a.startsWith('--task='))?.slice(7);
if (!task) throw new Error('Usage: npm start -- --task="Your concise task" [--auto] [--session=/path/to/session.jsonl]');
const directory = join(process.cwd(), '.runtime', 'interactive');
const judge = new LayaJudge();
let session;
try {
  await judge.ready;
  mkdirSync(directory, { recursive: true });
  let gc: ContextGC;
  const post = new PostToolGC(judge, () => gc?.task ?? task, event => {
    appendFileSync(join(directory, 'post-tool.jsonl'), JSON.stringify({ time: new Date().toISOString(), ...event }) + '\n');
  });
  session = await makeSession({ runtime: await subscriptionRuntime(), directory, tools: ['read', 'bash', 'edit', 'write'],
    sessionFile: process.argv.find(a => a.startsWith('--session='))?.slice(10),
    extensions: [post.extension, toolFilter({ judge: (_originalTask, tail) => judge.judge(gc?.task ?? task, tail) },
      task, join(directory, 'artifacts'), (process.env.GC_FILTER_TOOLS ?? '').split(',').filter(Boolean))],
    system: `You are a coding assistant. Current task: ${task}. Work carefully and keep replies concise.`,
  });
  gc = new ContextGC(session, judge, task, join(directory, 'decisions.jsonl'), process.argv.includes('--auto') ? 'auto' : 'shadow');
  const rl = createInterface({ input: stdin, output: stdout });
  console.log(`Session: ${session.sessionFile}\nGC mode: ${gc.mode}. /checkpoint, /restore ENTRY, /task TEXT, /exit`);
  try {
    for (;;) {
      const line = await rl.question('> ');
      if (line === '/exit') break;
      if (line === '/checkpoint') { gc.promote(); console.log(gc.checkpoint); continue; }
      if (line.startsWith('/restore ')) { await gc.restore(line.slice(9).trim()); continue; }
      if (line.startsWith('/task ')) {
        const updated = line.slice(6).trim();
        if (!updated) continue;
        console.log((await prompt(session, `Task update: ${updated}`)).answer);
        gc.task = updated; gc.promote(); continue;
      }
      if (!line.trim()) continue;
      const result = await prompt(session, line);
      console.log(result.answer);
      const decision = await post.settle(gc) ?? await gc.collect();
      console.log(`[GC ${decision.action}: ${decision.reason}; leaf ${decision.leaf}]`);
    }
  } finally { rl.close(); }
} finally { session?.dispose(); judge.close(); }

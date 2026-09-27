import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { subscriptionRuntime, makeSession, prompt } from './runtime.js';

const directory = mkdtempSync(join(tmpdir(), 'pi-health-'));
try {
  const runtime = await subscriptionRuntime();
  const session = await makeSession({ runtime, directory, tools: [] });
  try { console.log((await prompt(session, 'Reply OK.')).answer); }
  finally { session.dispose(); }
} catch (error) { console.error(String(error)); process.exitCode = 1; }
finally { rmSync(directory, { recursive: true, force: true }); }

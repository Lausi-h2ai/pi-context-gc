# Optional JavaScript/TypeScript general benchmark

`general-js-tasks.ts` is an independent catalog for Node based repair tasks. It
does not alter the frozen Python catalog or its runner. The catalog currently
contains four tasks:

| Task | Entry/export | Domain | Hidden cases | Fixture |
| --- | --- | --- | ---: | --- |
| `general-js-config` | `src/config.js` / `loadConfig` | layered service configuration | 6 | short |
| `general-js-router` | `src/router.js` / `routeRequest` | HTTP route matching | 6 | long |
| `general-js-cache` | `src/cache.js` / `runCache` | TTL and LRU cache | 5 | short |
| `general-js-scheduler` | `src/index.ts` / `planJobs` | TypeScript worker scheduling | 6 | long |

Each workspace contains a `package.json` with a dependency free `npm test`
script, a public `test/` directory, two source or model files, and the public
contract and deterministic log fixtures. The source is intentionally broken in
more than one file. The turn sequence asks a candidate to inspect the contract,
all related files, and the public npm tests before editing.

## Interface

The integration adapter should treat `GeneralJsTask` as the task contract:

```ts
interface GeneralJsTask {
  id: string;
  objective: string;
  initial: string;
  requirements: string;
  entry: string;
  exportName: string;
  files: Readonly<Record<string, string>>;
  cases: readonly GeneralJsCase[];
  turns: readonly GeneralJsTurn[];
  fixture: { diagnostic: string; aside: string; stratum: 'short' | 'long' };
  publicTestCommand: readonly string[];
}

interface GeneralJsCase {
  name: string;
  args: readonly unknown[];
  expected?: unknown;
  throws?: string;
  mutateInputAfter?: { path: readonly (string | number)[]; value: unknown };
}
```

Use `prepareGeneralJsWorkspace(task, workspace)` before the scripted turns and
`evaluationRequest(task, workspace)` when invoking the evaluator. A future
benchmark adapter can map the fields to the existing general benchmark's
`objective`, `requirements`, `files`, `turns`, and fixture concepts without
changing the current catalog while a run is frozen.

## Hidden evaluator boundary

Run `node benchmarks/general-js-evaluate.mjs` with one JSON request on stdin.
`evaluateGeneralJsTask` is a convenience host wrapper for this protocol. The
request contains hidden cases and expected values only in the evaluator's
stdin. Before each case, the evaluator runs the candidate's `npm test` command
in the candidate workspace. For each hidden case it launches a fresh child
process and sends only:

```json
{
  "workspace": "/absolute/candidate/workspace",
  "entry": "src/config.js",
  "exportName": "loadConfig",
  "args": [{}, {}]
}
```

The child imports the entry module, calls the export, captures ordinary
`stdout`, and emits one JSON document after restoring the protocol stream. It
never receives the case name or expected value. A worker result is checked for
strict JSON value equality, built-in error identity, argument mutation, and
return-value aliasing. Public tests and hidden cases run in separate processes;
the evaluator never writes hidden cases into the workspace.

`general-js-evaluate-test.mjs` exercises this boundary with adversarial
candidate modules: a forged evaluator marker is captured, a non-built-in error
with a matching name is rejected, and a candidate that writes directly to file
descriptor 1 cannot forge a successful host response.

## Running the extension

The extension intentionally has no package dependency beyond the Node runtime
(the repository's existing `tsx` is needed only to import its TypeScript
catalog). A focused check can use:

```bash
npx tsx -e "import { generalJsTasks, prepareGeneralJsWorkspace, evaluateGeneralJsTask } from './benchmarks/general-js-tasks.ts'; import { mkdtempSync } from 'node:fs'; import { tmpdir } from 'node:os'; import { join } from 'node:path'; const task = generalJsTasks[0]; const workspace = mkdtempSync(join(tmpdir(), 'general-js-')); prepareGeneralJsWorkspace(task, workspace); console.log(evaluateGeneralJsTask(task, workspace));"
node benchmarks/general-js-evaluate-test.mjs
```

The initial fixtures are expected to fail hidden or public cases. A repaired
copy can be checked with the same adapter. The long diagnostics contain 160
deterministic informational lines followed by one actionable line; the short
diagnostics contain six timestamped lines. No network, random data, generated
timestamps, or npm installation is used.

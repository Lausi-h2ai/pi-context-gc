# Offline archiving demo

```bash
npm ci
npm run demo
```

Requires Node.js 24. No Python dependencies, model download, GPU, authentication, or provider requests are used.

`archive.ts` runs the production `generalContextPolicy` context handler on a synthetic diagnostic result. It uses a deterministic `KEEP_FULL` verdict to demonstrate that the budget can override that vote. It then reads the archived file and checks equality and SHA-256. The original log is retained under `.runtime/demo/artifacts/`; `.runtime/demo/replay.json` describes the execution.

The demo is a mechanism check. There is no live coding agent making the recovery decision, and the character reduction of one log is not a benchmark token-saving estimate. Reference length varies with the absolute checkout path.

## Regenerate the visuals

The GIF is a 15-second visual replay of this demo's output. The PNG/SVG chart is built from all 24 final v3 result files. Media dependencies are optional and separate from the runtime:

```bash
python3 -m venv .runtime/media-venv
.runtime/media-venv/bin/pip install matplotlib pillow
npm run demo
.runtime/media-venv/bin/python demo/render_assets.py
```

Outputs are written to `docs/assets/`. The animation identifies the synthetic log and deterministic judge on every frame. The chart includes cached and uncached input, task pass counts, and the limits on interpreting the result.

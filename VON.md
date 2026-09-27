# Local Von judge

The optional `VonJudge` adapter runs Von in a persistent local Python worker. It uses `von-sdk==1.2.3`, model `von-1.2.0`, and the pinned public Hub snapshot `wfzyx/von@5df8185a4f2327ad0a7cd117cc4f701ac557b9ae`. The worker uses Von's in-process `system_one` API and clears hosted endpoint and API-key environment variables, so no inference API key is required.

Install the pinned Python environment with:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
```

The first `VonJudge` startup downloads approximately 3 GB of model files into the Hugging Face cache and warms the encoder. Later starts reuse that snapshot. The measured cached startup on the RTX 3070 was 7.2 seconds; one retention request took 42 ms wall time (42 ms reported worker inference latency). The first uncached setup fetched the six files in roughly 34 seconds before loading the model.

By default the adapter uses `.venv/bin/python` and `python/von-judge.py`. Set `VON_PYTHON` to another interpreter, or pass `checkpointDir` / `VON_CHECKPOINT_DIR` when the pinned files are already available locally. Set `VON_OFFLINE=1` to require a cached snapshot and fail startup instead of attempting a download. `VON_DEVICE=cuda` selects the CUDA device; the SDK also supports CPU fallback.

Example smoke invocation:

```bash
npx tsx -e "import { VonJudge } from './src/von-judge.ts'; (async()=>{const judge=new VonJudge(); console.log(await judge.ready); console.log(await judge.judge('Fix the parser', 'The exact failing assertion is required.')); judge.close();})()"
```

Startup, model loading, oversized input, and malformed response errors reject the judge call. The context collector treats a rejected judge as a keep decision, so the retention path fails open.

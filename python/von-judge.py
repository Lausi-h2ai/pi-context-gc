"""Persistent local Von JSONL retention judge.

Stdout is reserved for the adapter protocol.  Von diagnostics and model load
messages are redirected to stderr so a stray library print cannot corrupt a
pending request.  This worker never constructs a remote client and never uses
an API key: the model is downloaded from the public Hub once (or loaded from
VON_CHECKPOINT_DIR) and all inference happens in this process.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import sys
import time
from typing import Any

VON_MODEL_ID = os.environ.get("VON_MODEL", "von-1.2.0")
VON_BACKEND = os.environ.get("VON_BACKEND", "von-1.2")
VON_HF_REPO = os.environ.get("VON_HF_REPO", "wfzyx/von")
VON_HF_REVISION = os.environ.get(
    "VON_HF_REVISION", "5df8185a4f2327ad0a7cd117cc4f701ac557b9ae"
)
MAX_STATE_TOKENS = 7_600
MAX_TASK_TOKENS = 256

RETENTION_QUESTION = {
    "type": "choice",
    "instructions": "How should this conversation tail be retained for the current coding task?",
    "criteria": {
        "KEEP_FULL": "The exact conversation details, code, requirements, facts, decisions, or complete output are needed to continue the task.",
        "KEEP_RESULT": "A useful conclusion, result, failure diagnosis, or new constraint should remain, while routine detail can be shortened.",
        "EXTERNALIZE": "The tail is a large useful artifact that can be archived and replaced by a compact reference.",
        "DISCARD": "The tail is an unrelated or redundant tangent and removing it loses no information needed for the current task.",
    },
}
DURABLE_QUESTION = {
    "type": "choice",
    "instructions": "Would forgetting this tail lose useful knowledge for the current coding task?",
    "criteria": {
        "yes": "Useful information, requirements, facts, decisions, code details, errors, or changes would be lost.",
        "no": "Nothing useful for the task would be lost; the tail is redundant, routine, or unrelated.",
    },
}


def _finite_probability(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Von returned invalid {name}") from exc
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError(f"Von returned invalid {name}")
    return number


def _load_von():
    # Make local-only behavior explicit even when the parent shell happens to
    # contain credentials or a hosted Von endpoint configuration.
    for name in (
        "VON_BASE_URL",
        "VON_API_KEY",
        "TYPESAFE_API_KEY",
        "HF_TOKEN",
        "HUGGINGFACE_HUB_TOKEN",
    ):
        os.environ.pop(name, None)

    import von
    from von.engine import VonEngine

    # Set the versioned backend before constructing the singleton.  Von 1.2's
    # independent option mode is selected by marker_calibration.json.
    von.set_backend(VON_BACKEND)

    checkpoint_dir = os.environ.get("VON_CHECKPOINT_DIR")
    if checkpoint_dir is None:
        # Download the exact public model snapshot instead of allowing the SDK
        # fallback to resolve a moving Hub revision.  token=False ensures no
        # API key is consulted for this public artifact.
        from huggingface_hub import snapshot_download

        checkpoint_dir = snapshot_download(
            repo_id=VON_HF_REPO,
            revision=VON_HF_REVISION,
            allow_patterns=[
                "config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "model.safetensors",
                "option_marker.pt",
                "marker_calibration.json",
            ],
            token=False,
            local_files_only=os.environ.get("VON_OFFLINE", "") == "1",
        )

    # The released Python API does not expose checkpoint_dir on VonEngine's
    # constructor.  Its backend does expose the selected local directory, so
    # set it before the first model load.  This keeps the worker on the pinned
    # snapshot without forking Von's inference implementation.
    engine = VonEngine.get_instance()
    backend = getattr(engine, "backend", None)
    if backend is None or not hasattr(backend, "checkpoint_dir"):
        raise RuntimeError("Unsupported von-sdk: Option-Marker backend is unavailable")
    backend.checkpoint_dir = checkpoint_dir

    # Constructing the local client explicitly avoids the SDK's environment
    # based remote mode.  A warmup forces missing weights/dependencies to fail
    # before the ready marker is emitted.
    client = von.VonClient(local=True)
    with contextlib.redirect_stdout(sys.stderr):
        client.system_one(
            state="worker startup",
            questions={"retention": RETENTION_QUESTION, "durable": DURABLE_QUESTION},
            model=VON_MODEL_ID,
        )
    model = getattr(backend, "_model", None)
    tokenizer = getattr(model, "tokenizer", None)
    if tokenizer is None:
        raise RuntimeError("Von did not expose a tokenizer after warmup")
    return von, client, tokenizer


def _judge(von: Any, client: Any, tokenizer: Any, task: str, tail: str) -> dict[str, Any]:
    task_ids = tokenizer.encode(task, add_special_tokens=False)
    if len(task_ids) > MAX_TASK_TOKENS:
        raise ValueError(f"Task exceeds {MAX_TASK_TOKENS} Von tokens; provide a concise task definition")
    state = f"Current coding task:\n{task}\n\nConversation tail:\n{tail}"
    state_ids = tokenizer.encode(state, add_special_tokens=False)
    if len(state_ids) > MAX_STATE_TOKENS:
        raise ValueError(
            f"Tail exceeds the local Von context budget ({MAX_STATE_TOKENS} tokens); retain it"
        )

    started = time.perf_counter()
    with contextlib.redirect_stdout(sys.stderr):
        response = client.system_one(
            state=state,
            questions={"retention": RETENTION_QUESTION, "durable": DURABLE_QUESTION},
            model=VON_MODEL_ID,
        )
    retention = response.answers["retention"]
    durable = response.answers["durable"]
    probabilities = getattr(retention, "probabilities", None)
    if not isinstance(probabilities, dict):
        raise ValueError("Von response omitted retention probabilities")
    action = getattr(retention, "choice", None)
    if action not in ("KEEP_FULL", "KEEP_RESULT", "EXTERNALIZE", "DISCARD"):
        raise ValueError("Von returned an invalid retention action")
    durable_probabilities = getattr(durable, "probabilities", None)
    if not isinstance(durable_probabilities, dict):
        raise ValueError("Von response omitted durable probabilities")
    discard_probability = _finite_probability(probabilities.get("DISCARD"), "discardProbability")
    durable_probability = _finite_probability(durable_probabilities.get("yes"), "durableProbability")
    raw = response.model_dump() if hasattr(response, "model_dump") else response
    return {
        "action": action,
        "discardProbability": discard_probability,
        "durableProbability": durable_probability,
        "windows": 1,
        "latencyMs": (time.perf_counter() - started) * 1000.0,
        "raw": raw,
    }


def main() -> None:
    try:
        with contextlib.redirect_stdout(sys.stderr):
            von, client, tokenizer = _load_von()
    except Exception as exc:
        # Startup exceptions are intentionally fatal.  The TypeScript host
        # rejects `ready`; its caller retains the tail on a failed judge.
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), flush=True)
        raise

    print(
        json.dumps(
            {
                "ready": True,
                "model": VON_MODEL_ID,
                "backend": VON_BACKEND,
                "repository": VON_HF_REPO,
                "revision": VON_HF_REVISION,
                "version": getattr(von, "__version__", None),
                "device": str(getattr(getattr(client, "_client", None), "device", "local")),
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        request: Any = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            request_id = request.get("id")
            if not isinstance(request_id, int):
                raise ValueError("request id must be an integer")
            task, tail = request.get("task"), request.get("tail")
            if not isinstance(task, str) or not isinstance(tail, str):
                raise ValueError("task and tail must be strings")
            result = _judge(von, client, tokenizer, task, tail)
            result["id"] = request_id
            print(json.dumps(result), flush=True)
        except Exception as exc:
            error: dict[str, Any] = {
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(json.dumps(error), flush=True)


if __name__ == "__main__":
    main()

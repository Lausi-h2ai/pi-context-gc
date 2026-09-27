"""Persistent, local-only Laya JSONL worker. Stdout is reserved for the protocol."""
import contextlib
import json
import os
import sys
import time

QUESTIONS = {
    "retention": {
        "type": "choice",
        "instructions": "How should this conversation tail be retained for the current task?",
        "criteria": {
            "KEEP_FULL": "Exact details are needed to continue the task.",
            "KEEP_RESULT": "A useful conclusion or new constraint must be kept.",
            "EXTERNALIZE": "A large useful artifact can be stored and referenced.",
            "DISCARD": "An unrelated tangent with no useful task information.",
        },
    },
    "durable": {
        "type": "choice",
        "instructions": "Would forgetting this tail lose useful task knowledge, changes, constraints or decisions?",
        "criteria": {"yes": "Useful information would be lost.", "no": "Nothing useful would be lost."},
    },
}


def main():
    with contextlib.redirect_stdout(sys.stderr):
        import laya
        import torch
        from huggingface_hub import snapshot_download
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        model = os.environ.get("LAYA_MODEL", "convaiinnovations/laya")
        revision = os.environ.get("LAYA_REVISION", "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851" if model == "convaiinnovations/laya" else "main")
        model_path = model if os.path.isdir(model) else snapshot_download(model, revision=revision,
            allow_patterns=["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*"])
        agent = laya.load(model_path, device=os.environ.get("LAYA_DEVICE", "cuda" if torch.cuda.is_available() else "cpu"))
    print(json.dumps({"ready": True, "model": model, "revision": os.path.basename(model_path),
                      "device": str(agent.device), "version": laya.__version__, "torch": torch.__version__,
                      "parameters": sum(p.numel() for p in agent.model.parameters())}), flush=True)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            start = time.perf_counter()
            task, tail = request["task"], request["tail"]
            task_ids = agent.tok.encode(task, add_special_tokens=False)
            # Never silently drop task constraints or the middle/end of a long tail.
            # An oversized task fails closed in the host; each tail window repeats it.
            if len(task_ids) > 100:
                raise ValueError("Task exceeds 100 Laya tokens; provide a concise task definition")
            prefix = f"Current task: {task}\nConversation tail:\n"
            budget = int(agent.cfg["max_len"]) - int(agent.cfg["head_max_len"]) - len(agent.tok.encode(prefix, add_special_tokens=False)) - 24
            if budget < 32:
                raise ValueError("Insufficient Laya context budget")
            ids = agent.tok.encode(tail, add_special_tokens=False)
            if len(ids) > 12000:
                raise ValueError("Tail exceeds local judge budget; retain it")
            step = max(1, budget - 24)
            states = [prefix + agent.tok.decode(ids[i:i + budget]) for i in range(0, max(1, len(ids)), step)]
            for state in states:
                if len(agent.tok.encode(state, add_special_tokens=False)) > int(agent.cfg["max_len"]) - int(agent.cfg["head_max_len"]) - 4:
                    raise ValueError("Window would be truncated; retain it")
            with contextlib.redirect_stdout(sys.stderr):
                # Serial windows bound GPU memory independently of document length.
                windows = [agent.predict(state, QUESTIONS) for state in states]
            discards = [r["answers"]["retention"]["probabilities"]["DISCARD"] for r in windows]
            durable = [r["answers"]["durable"]["probabilities"]["yes"] for r in windows]
            choices = [r["answers"]["retention"]["choice"] for r in windows]
            action = next((a for a in ["KEEP_FULL", "KEEP_RESULT", "EXTERNALIZE"] if a in choices), "DISCARD")
            response = {"id": request["id"], "action": action, "discardProbability": min(discards),
                        "durableProbability": max(durable), "windows": len(windows),
                        "latencyMs": (time.perf_counter() - start) * 1000, "raw": windows}
        except Exception as exc:
            response = {"id": request.get("id") if isinstance(locals().get("request"), dict) else None,
                        "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()

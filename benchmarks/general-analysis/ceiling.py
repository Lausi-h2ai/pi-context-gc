#!/usr/bin/env python3
"""Estimate the upper bound on savings the context policy can reach.

The paired report in ``analyze.py`` measures what a run *did*.  This script
measures what the policy *could* do on the same workload, which separates
"the judge chose badly" from "there was nothing eligible to remove".

For every baseline trial the script replays the recorded session, rebuilds the
message context in front of each model request, and sums the tool-result
characters that ``generalContextPolicy`` would consider a candidate: a
non-error, text-only tool result from an earlier turn, not a protected read,
and at least ``minimumCharacters`` long.  Removal is additionally capped by the
policy budget of ``1 - retainedFraction`` of all message characters.

A request contributes at most ``min(candidates, budget)`` characters.  Totals
compare that removed volume with the characters actually sent, so the reported
ratio is a ceiling: no judge can exceed it on this workload.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import Any, Iterable

SAFE = {"minimumCharacters": 1500, "protectedReadBasenames": ["requirements.txt", "project-guide.md", "solver.py"]}
AGGRESSIVE = {"minimumCharacters": 600, "protectedReadBasenames": ["requirements.txt", "solver.py"]}
POLICIES = {"safe": SAFE, "aggressive": AGGRESSIVE}
DEFAULT_RETAINED_FRACTION = 0.70


def session_file(trial: Path) -> str | None:
    matches = sorted(glob.glob(str(trial / "session" / "*.jsonl")))
    return matches[0] if matches else None


def messages(path: str) -> list[dict[str, Any]]:
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("type") == "message":
                out.append(record["message"])
    return out


def block_text(message: dict[str, Any]) -> str | None:
    """Return joinable text when the result is text-only, else None."""

    blocks = message.get("content")
    if not isinstance(blocks, list) or not blocks:
        return None
    if any(not isinstance(block, dict) or block.get("type") != "text" for block in blocks):
        return None
    return "\n".join(block.get("text") or "" for block in blocks)


def read_paths(messages_before: Iterable[dict[str, Any]]) -> dict[str, str]:
    paths: dict[str, str] = {}
    for message in messages_before:
        if message.get("role") != "assistant":
            continue
        for block in message.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "toolCall" or block.get("name") != "read":
                continue
            path = (block.get("arguments") or {}).get("path")
            if isinstance(path, str):
                paths[block.get("id")] = path
    return paths


def request_ceilings(context: list[dict[str, Any]], policy: dict[str, Any], retained_fraction: float,
                     sent: int | None = None) -> tuple[int, int]:
    """Return (removable characters, sent characters) for one context.

    ``sent`` is the provider payload size for this request when known.  It is the
    same currency as the removable text, whereas reserializing the session log
    would add per-message metadata that the provider never receives.
    """

    total = sent if sent is not None else sum(len(json.dumps(message)) for message in context)
    last_user = -1
    for index in range(len(context) - 1, -1, -1):
        if context[index].get("role") == "user":
            last_user = index
            break
    if last_user < 0:
        return 0, total
    paths = read_paths(context[:last_user])
    protected = set(policy["protectedReadBasenames"])
    minimum = policy["minimumCharacters"]
    eligible = 0
    for index in range(last_user):
        message = context[index]
        if message.get("role") != "toolResult" or message.get("isError"):
            continue
        path = (paths.get(message.get("toolCallId")) or "").replace("\\", "/")
        if path and path.split("/")[-1] in protected:
            continue
        text = block_text(message)
        if text is None or len(text) < minimum:
            continue
        eligible += len(text)
    budget = max(0, int(total * (1 - retained_fraction)))
    return min(eligible, budget), total


def analyse_trial(trial: Path, retained_fraction: float) -> dict[str, Any]:
    path = session_file(trial)
    if not path:
        return {"id": trial.name, "error": "no session log"}
    log = messages(path)
    telemetry = trial / "telemetry.json"
    sizes: list[int] = []
    if telemetry.is_file():
        sizes = [row.get("inputCharacters") or 0 for row in json.loads(telemetry.read_text()).get("requests", [])]
    totals = {name: {"removable": 0, "sent": 0} for name in POLICIES}
    requests = 0
    for index, message in enumerate(log):
        if message.get("role") != "assistant":
            continue
        context = log[:index]
        sent = sizes[requests] if requests < len(sizes) else None
        for name, policy in POLICIES.items():
            removable, request_total = request_ceilings(context, policy, retained_fraction, sent)
            totals[name]["removable"] += removable
            totals[name]["sent"] += request_total
        requests += 1
    return {"id": trial.name, "requests": requests, "totals": totals}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("results/general-v2-r1"))
    parser.add_argument("--retained-fraction", type=float, default=DEFAULT_RETAINED_FRACTION)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.directory.resolve()
    design = json.loads((root / "design.json").read_text())
    strata = {task["id"]: task.get("stratum", "unknown") for task in design["design"]["tasks"]}

    per_trial = []
    for trial in sorted(root.iterdir()):
        if not (trial / "result.json").is_file():
            continue
        result = json.loads((trial / "result.json").read_text())
        if result.get("error") or result.get("arm") != "baseline":
            continue
        row = analyse_trial(trial, args.retained_fraction)
        row["task"] = result["task"]
        row["stratum"] = result.get("stratum") or strata.get(result["task"], "unknown")
        row["inputTotal"] = result.get("inputTotal")
        per_trial.append(row)

    grouped: dict[str, dict[str, dict[str, int]]] = {}
    for row in per_trial:
        for key in (row.get("stratum", "unknown"), "ALL"):
            bucket = grouped.setdefault(key, {name: {"removable": 0, "sent": 0} for name in POLICIES})
            for name in POLICIES:
                bucket[name]["removable"] += row["totals"][name]["removable"]
                bucket[name]["sent"] += row["totals"][name]["sent"]

    print(f"# Ceiling analysis: {root.name}")
    print(f"\nBaseline trials: {len(per_trial)}; removal budget {1 - args.retained_fraction:.0%} of message characters.\n")
    print("| Stratum | Trials | Safe 1500ch ceiling | Aggressive 600ch ceiling |")
    print("| --- | ---: | ---: | ---: |")
    for key in ["long", "short", "ALL"]:
        if key not in grouped:
            continue
        bucket = grouped[key]
        count = len({row["id"] for row in per_trial if row.get("stratum", "unknown") == key or key == "ALL"})
        cells = []
        for name in ("safe", "aggressive"):
            sent = bucket[name]["sent"]
            removable = bucket[name]["removable"]
            cells.append(f"{removable / sent:.1%}" if sent else "n/a")
        print(f"| {key} | {count} | {cells[0]} | {cells[1]} |")

    print("\n## Per trial (baseline)\n")
    print("| Trial | Stratum | Requests | Safe ceiling | Aggressive ceiling | Input tokens |")
    print("| --- | --- | ---: | ---: | ---: | ---: |")
    for row in per_trial:
        cells = []
        for name in ("safe", "aggressive"):
            sent = row["totals"][name]["sent"]
            cells.append(f"{row['totals'][name]['removable'] / sent:.1%}" if sent else "n/a")
        print(f"| {row['id']} | {row.get('stratum')} | {row.get('requests')} | {cells[0]} | {cells[1]} | {row.get('inputTotal'):,} |")

    if args.out:
        args.out.write_text(json.dumps({"directory": str(root), "trials": per_trial, "grouped": grouped}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

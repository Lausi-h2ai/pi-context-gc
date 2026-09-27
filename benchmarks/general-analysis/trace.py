#!/usr/bin/env python3
"""Trace per-request payload sizes for one task across the arms of a run.

``analyze.py`` reports one total per trial, and ``ceiling.py`` reports what was
available.  Neither shows *when* a prune took effect or how the agent responded
to it.  This script prints the request-by-request provider payload for one task
so a saving can be attributed to a specific point in the conversation, and so a
candidate that did more work than the baseline is visible as a positive delta.

```bash
python3 benchmarks/general-analysis/trace.py results/general-v2-r1 config-merge
```
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def payload(path: Path) -> list[int]:
    telemetry = path / "telemetry.json"
    if not telemetry.is_file():
        return []
    return [row.get("inputCharacters") or 0 for row in json.loads(telemetry.read_text())["requests"]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("task")
    parser.add_argument("--baseline", default="baseline")
    args = parser.parse_args()

    root = args.directory.resolve()
    directories: dict[str, Path] = {}
    totals: dict[str, dict[str, int]] = {}
    for trial in sorted(root.iterdir()):
        if not (trial / "result.json").is_file():
            continue
        result = json.loads((trial / "result.json").read_text())
        if result.get("task") != args.task or result.get("error"):
            continue
        directories[result["arm"]] = trial
        totals[result["arm"]] = {k: result.get(k) or 0 for k in ("inputTotal", "requests", "prunedResults", "removedToolCharacters")}

    if args.baseline not in totals:
        print(f"no completed {args.baseline} trial for {args.task}")
        return 1
    candidates = sorted(arm for arm in totals if arm != args.baseline)

    base = payload(directories[args.baseline])
    print(f"# {args.task} in {root.name}")
    print(f"\nBaseline requests: {len(base)}; total input {totals[args.baseline]['inputTotal']:,} tokens.\n")
    print("| req | baseline | " + " | ".join(candidates) + " | " + " | ".join(f"delta {c}" for c in candidates) + " |")
    print("| ---: | ---: | " + " | ".join("---:" for _ in candidates) + " | " + " | ".join("---:" for _ in candidates) + " |")
    series = {c: payload(directories[c]) for c in candidates}
    rows = max([len(base)] + [len(v) for v in series.values()])
    for index in range(rows):
        cells = [str(base[index]) if index < len(base) else "-"]
        cells += [str(series[c][index]) if index < len(series[c]) else "-" for c in candidates]
        deltas = [f"{series[c][index] - base[index]:+,}" if index < len(base) and index < len(series[c]) else "-" for c in candidates]
        print(f"| {index} | " + " | ".join(cells) + " | " + " | ".join(deltas) + " |")

    print("\n| Arm | Requests | Input total | Saved | Removed characters | Applied prunes |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for arm in [args.baseline, *candidates]:
        row = totals[arm]
        saved = totals[args.baseline]["inputTotal"] - row["inputTotal"]
        share = f"{saved / totals[args.baseline]['inputTotal']:+.1%}" if totals[args.baseline]["inputTotal"] else "-"
        print(f"| {arm} | {row['requests']} | {row['inputTotal']:,} | {share} | {row['removedToolCharacters']:,} | {row['prunedResults']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

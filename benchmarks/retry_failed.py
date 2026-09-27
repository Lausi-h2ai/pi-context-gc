"""Archive provider-failed benchmark trials so the unchanged runner can resume them."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, nargs="?", default=Path("results/coding-factorial"))
args = parser.parse_args()
root = args.directory.resolve()
archive = root / "infrastructure-failures"
moved = []
for result_path in sorted(root.glob("*/result.json")):
    result = json.loads(result_path.read_text())
    if not result.get("error"):
        continue
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = archive / f"{result_path.parent.name}-{stamp}"
    counter = 1
    while destination.exists():
        destination = archive / f"{result_path.parent.name}-{stamp}-{counter}"
        counter += 1
    archive.mkdir(exist_ok=True)
    shutil.move(str(result_path.parent), str(destination))
    moved.append((result["id"], str(destination)))
for trial_id, destination in moved:
    print(f"Archived {trial_id}: {destination}")
print(f"{len(moved)} failed trials ready to retry")

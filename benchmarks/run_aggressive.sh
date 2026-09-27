#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results
exec > >(tee -a results/aggressive-run.log) 2>&1
echo "Aggressive benchmark started: $(date -u --iso-8601=seconds)"
trap 'status=$?; echo "Aggressive benchmark exited with status $status: $(date -u --iso-8601=seconds)"' EXIT
python3 benchmarks/retry_failed.py results/coding-aggressive-pilot
npm run benchmark -- --aggressive --out=results/coding-aggressive-pilot --repeats=1
python3 benchmarks/analyze_aggressive.py results/coding-aggressive-pilot

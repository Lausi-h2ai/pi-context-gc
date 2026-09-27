#!/usr/bin/env bash
# Wait for the ChatGPT subscription quota to return, then resume a general run.
#
# Usage: benchmarks/run_when_quota.sh [output-directory] [policy]
#
# The provider usage limit rejects every request until the rolling window
# resets.  This script probes with the single-request healthcheck instead of
# starting the benchmark, so a rejected run does not consume trial directories
# or archive real trial artifacts.
set -uo pipefail
cd "$(dirname "$0")/.."

OUT=${1:-results/general-v3-aggressive-r1}
POLICY=${2:-aggressive}
LOG=${LOG:-results/quota-watch.log}
PROBE_INTERVAL=${PROBE_INTERVAL:-300}
MAX_PROBES=${MAX_PROBES:-60}
PROBE_OUT=$(mktemp)

exec >>"$LOG" 2>&1
trap 'status=$?; echo "quota watch exited with status $status: $(date -u --iso-8601=seconds)"; rm -f "$PROBE_OUT"' EXIT
echo "=== quota watch started: $(date -u --iso-8601=seconds) out=$OUT policy=$POLICY"

classify() {
  local text
  text=$(cat "$PROBE_OUT")
  case "$text" in
    *"usage limit"*)            echo "QUOTA" ;;
    *"auth.json"*|*"OAuth login"*|*"token has expired"*) echo "AUTH" ;;
    *)                          echo "OTHER" ;;
  esac
}

probe=0
until npm run --silent healthcheck >"$PROBE_OUT" 2>&1; do
  probe=$((probe + 1))
  echo "[$(date -u --iso-8601=seconds)] probe $probe rejected [$(classify)]: $(tail -c 300 "$PROBE_OUT" | tr '\n' ' ')"
  if [ "$probe" -ge "$MAX_PROBES" ]; then echo "giving up after $probe probes"; exit 2; fi
  sleep "$PROBE_INTERVAL"
done
echo "[$(date -u --iso-8601=seconds)] probe $probe succeeded: $(tail -c 120 "$PROBE_OUT" | tr '\n' ' ')"

python3 benchmarks/retry_failed.py "$OUT"
npm run benchmark:general -- --out="$OUT" --policy="$POLICY" --repeats=1
python3 benchmarks/general-analysis/analyze.py "$OUT" --baseline baseline --treatments laya von --check-gate

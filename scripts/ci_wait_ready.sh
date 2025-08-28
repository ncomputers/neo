#!/usr/bin/env bash
set -euo pipefail

LOG_FILE=${1:-api.log}

if ! npx --yes wait-on tcp:localhost:8000 --timeout 60000; then
  echo "Port 8000 did not open in time" >&2
  ps aux
  [[ -f "$LOG_FILE" ]] && cat "$LOG_FILE"
  exit 1
fi

for i in {1..40}; do
  if curl -fsS --max-time 5 http://localhost:8000/ready; then
    exit 0
  fi
  sleep 2
done

echo "API not ready" >&2
ps aux
[[ -f "$LOG_FILE" ]] && cat "$LOG_FILE"
exit 1

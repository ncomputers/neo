#!/usr/bin/env bash
set -euo pipefail
SKIP_DB_MIGRATIONS=1 python start_app.py &
for i in {1..40}; do
  curl -fsS http://localhost:8000/ready && exit 0
  sleep 2
done
echo "API not ready" >&2
exit 1

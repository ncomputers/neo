#!/usr/bin/env bash
set -Eeuo pipefail

: "${WEBHOOK:?WEBHOOK is required}"
ENV_NAME="${1:-prod}"
STEP_FAILED="${2:-unknown}"

# Build JSON safely
payload="$(jq -n --arg t "synthetic monitor ${ENV_NAME} failed step=${STEP_FAILED}" '{text:$t}')"

curl -sS -X POST \
  -H 'Content-Type: application/json' \
  --data "$payload" \
  "$WEBHOOK"

#!/bin/bash
set -euo pipefail

# URL to check for heartbeat
HEARTBEAT_URL=${HEARTBEAT_URL:?HEARTBEAT_URL not set}
EXPECTED_STATUS=${EXPECTED_STATUS:-200}

status=$(curl -s -o /dev/null -w "%{http_code}" "$HEARTBEAT_URL")

if [ "$status" != "$EXPECTED_STATUS" ]; then
  echo "Heartbeat failed with status $status" >&2
  if [ -n "${ALERT_COMMAND:-}" ]; then
    eval "$ALERT_COMMAND"
  fi
fi

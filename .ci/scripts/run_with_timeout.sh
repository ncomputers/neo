#!/usr/bin/env bash
set -u

TIMEOUT_DURATION="${CI_TIMEOUT:-15m}"

timeout "$TIMEOUT_DURATION" "$@"
status=$?
if [ $status -eq 124 ]; then
  echo "Command timed out after $TIMEOUT_DURATION" >&2
fi
exit $status

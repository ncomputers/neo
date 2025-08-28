#!/bin/bash
set -euo pipefail

# Build Android TWA wrappers
pushd android/admin-twa >/dev/null
if [ -x ./gradlew ]; then
  ./gradlew assembleRelease
else
  echo "gradlew not found: run bubblewrap init first" >&2
fi
popd >/dev/null

pushd android/kds-twa >/dev/null
if [ -x ./gradlew ]; then
  ./gradlew assembleRelease
else
  echo "gradlew not found: run bubblewrap init first" >&2
fi
popd >/dev/null

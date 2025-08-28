#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for app in admin-twa kds-twa; do
  echo "Building $app..."
  (cd "$ROOT/android/$app" && ./gradlew assembleRelease)
done

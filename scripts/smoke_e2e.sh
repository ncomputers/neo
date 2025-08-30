#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
RESET='\033[0m'
status=0

cd "$(dirname "$0")/.."

echo 'Running Playwright e2e tests'
if ! (cd e2e/playwright && npx playwright test --reporter=line); then
  status=1
fi

echo 'Running Playwright visual regression tests'
if ! npx playwright test -c playwright.vr.config.ts --reporter=line; then
  status=1
fi

echo 'Running Lighthouse CI checks'
if ! npx lhci autorun --config=lighthouserc.json \
  --collect.url=http://localhost:5173/guest/menu \
  --collect.url=http://localhost:5174/kds/expo \
  --collect.url=http://localhost:5175/admin/dashboard; then
  status=1
fi

if [ "$status" -eq 0 ]; then
  echo -e "${GREEN}smoke ok${RESET}"
else
  echo -e "${RED}smoke failed${RESET}" >&2
fi

exit $status

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DB_URL="${DATABASE_URL:-${POSTGRES_MASTER_URL:-}}"
if [[ -z "$DB_URL" ]]; then
  echo "DATABASE_URL or POSTGRES_MASTER_URL must be set" >&2
  exit 1
fi

export DATABASE_URL="$DB_URL"

alembic upgrade head "$@"

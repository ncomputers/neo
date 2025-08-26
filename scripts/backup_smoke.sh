#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_URL:?POSTGRES_URL is required}"
: "${BACKUP_PUBLIC_KEY:?BACKUP_PUBLIC_KEY is required}"
: "${BACKUP_PRIVATE_KEY:?BACKUP_PRIVATE_KEY is required}"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

DUMP="$TMPDIR/db.sql"
ENC="$DUMP.age"
TMP_DB="backup_smoke_$RANDOM"
BASE="${POSTGRES_URL%/*}"
ADMIN_URL="$BASE/postgres"
RESTORE_URL="$BASE/$TMP_DB"

start=$(date +%s)
pg_dump "$POSTGRES_URL" > "$DUMP"
age --encrypt -r "$BACKUP_PUBLIC_KEY" -o "$ENC" "$DUMP"
dump_time=$(( $(date +%s) - start ))
size=$(du -h "$ENC" | cut -f1)

psql "$ADMIN_URL" -c "DROP DATABASE IF EXISTS \"$TMP_DB\";" >/dev/null
psql "$ADMIN_URL" -c "CREATE DATABASE \"$TMP_DB\";" >/dev/null

KEY_FILE="$TMPDIR/key.txt"
printf '%s' "$BACKUP_PRIVATE_KEY" > "$KEY_FILE"
start=$(date +%s)
age --decrypt -i "$KEY_FILE" "$ENC" | psql "$RESTORE_URL" >/dev/null
restore_time=$(( $(date +%s) - start ))

psql "$ADMIN_URL" -c "DROP DATABASE \"$TMP_DB\";" >/dev/null

echo "size=$size dump_time=${dump_time}s restore_time=${restore_time}s"

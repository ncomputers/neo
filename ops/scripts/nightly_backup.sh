#!/bin/bash
set -euo pipefail

# Directory to store encrypted backups
BACKUP_DIR=${BACKUP_DIR:-/var/backups}
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMPFILE="$BACKUP_DIR/db_$TIMESTAMP.sql"

# Dump Postgres database
pg_dump "$POSTGRES_URL" > "$DUMPFILE"

# Encrypt the dump
SCRIPT_DIR=$(dirname "$0")
python "$SCRIPT_DIR/../../scripts/backup_encrypt.py" "$DUMPFILE"
ENCRYPTED="$DUMPFILE.age"

# Upload to S3/MinIO if configured
if [ -n "${S3_BUCKET:-}" ]; then
  aws s3 cp "$ENCRYPTED" "s3://$S3_BUCKET/" --endpoint-url "${S3_ENDPOINT:-}"
fi

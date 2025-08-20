# Backup & Disaster Recovery

## Backups
- Nightly `pg_dump` of master + all tenant DBs.
- Store to local disk and MinIO/S3 (encrypted).
- Retention per outlet policy (default 30/90 days).

## Restore
- Restore into staging DB first.
- Validate with smoke tests.
- Promote to prod during maintenance window.

## Drills
- Quarterly restore drill with checklist + sign-off.

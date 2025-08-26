# Backup & Disaster Recovery

## Backups
- Nightly `pg_dump` of master + all tenant DBs.
- Encrypt dumps with [`age`](https://age-encryption.org/) using
  `BACKUP_PUBLIC_KEY` from secrets.
- Store to local disk and MinIO/S3.
- Retention per outlet policy (default 30/90 days).

## Restore
- Decrypt `.age` dump with matching private key via
  ``BACKUP_PRIVATE_KEY``.
- Restore into staging DB first.
- Validate with smoke tests.
- Promote to prod during maintenance window.

## Drills
- Quarterly restore drill with checklist + sign-off.

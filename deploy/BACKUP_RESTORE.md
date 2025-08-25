# Backup and Restore

Utilities for exporting and restoring individual tenant databases.

## Backup

Create a backup file for a tenant database::

    python scripts/tenant_backup.py --tenant TENANT --out /backups/TENANT-YYYYMMDD.sql

## Restore

Restore a tenant database from a backup file::

    python scripts/tenant_restore.py --tenant TENANT --file /backups/TENANT-YYYYMMDD.sql

The restore command ensures the tenant database or schema exists before loading
the provided dump. For PostgreSQL backends, it invokes `psql` or `pg_restore` as
needed. SQLite tenants are loaded using `sqlite3`.

### Caution

Restoring will overwrite existing tenant data. Double‑check the target tenant
and backup file before running this command. Prefer performing restores during
maintenance windows and retain a copy of the previous data when possible.

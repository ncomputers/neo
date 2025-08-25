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

## Automation

Systemd unit and timer files automate nightly backups for all tenants.

1. Copy `systemd/neo-backup.service` and `systemd/neo-backup.timer`
   to `/etc/systemd/system/`.
2. Create `/etc/neo/tenants.env` with a space-separated list of IDs::

       TENANTS="tenant_a tenant_b"

3. Ensure `/var/backups/neo` exists.
4. Enable the timer::

       sudo systemctl daemon-reload
       sudo systemctl enable --now neo-backup.timer

The timer runs `scripts/tenant_backup.py` for each tenant daily at 03:00
and writes dumps to `/var/backups/neo`.

### Rotation

Prune old dumps to keep seven daily backups and four weekly snapshots.
A simple cron job::

       find /var/backups/neo -name '*.sql' -mtime +7 -delete
       find /var/backups/neo/weekly -name '*.sql' -mtime +28 -delete

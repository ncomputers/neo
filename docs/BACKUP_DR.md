# Backup & Disaster Recovery

## Database
- Nightly snapshot of master and tenant databases
- Retain last 7 days on cold storage

## Storage
- `rsync` static assets to off-site bucket daily

## Restore Drill
1. Provision fresh database from snapshot
2. Restore storage archive
3. Run `scripts/tenant_restore.py --tenant <id>`
4. Verify application health and data integrity

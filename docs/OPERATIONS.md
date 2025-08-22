# Operations

## Data Purge

The `scripts/purge_data.py` helper removes expired customer PII and delivered
notification outbox entries for a tenant. It expects the `POSTGRES_MASTER_URL`
for the master database and `POSTGRES_TENANT_DSN_TEMPLATE` for tenant databases
to be set in the environment.

```bash
python scripts/purge_data.py --tenant TENANT_NAME
```

### Example crontab

Run daily at 3 AM:

```
0 3 * * * cd /path/to/neo && python scripts/purge_data.py --tenant TENANT_NAME
```

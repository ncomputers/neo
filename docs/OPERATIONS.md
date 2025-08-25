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

## Support Bundle

Administrators can download a diagnostic archive for a tenant:

```
GET /api/outlet/{tenant}/support/bundle.zip
```

The ZIP includes:

- `env.txt` – masked environment flags
- `health.json` and `ready.json` – service health indicators
- `version.json` – git SHA and build timestamp
- `recent-logs.txt` – recent log lines or last 200 audit records
- `config.json` – tenant plan, feature flags, and limits


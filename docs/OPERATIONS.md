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

## Owner Digest

Operators can send a daily summary covering orders, average preparation
time, top selling items, complimentary counts, tip totals and webhook
breaker opens:

```bash
python scripts/owner_digest.py --tenant TENANT_NAME
```

### Example crontab

Run nightly at 20:00 IST:

```
0 20 * * * cd /path/to/neo && python scripts/owner_digest.py --tenant TENANT_NAME
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

## Preflight Checklist

Operators can verify service readiness before go‑live using a consolidated
checklist:

```
GET /api/admin/preflight
```

The endpoint returns overall status and results for individual checks covering
database and Redis connectivity, migration state, storage backend, webhook
configuration, Alertmanager reachability, backup recency, presence of partial
unique indexes for soft‑deleted rows, sanity of the quotas endpoint, webhook
breaker metrics, and replica gauge health.
configuration, quotas service, webhook metrics, replica health, Alertmanager
reachability, soft-delete indexes, and backup recency.

## Dead Letter Queue

Administrators can inspect and replay failed webhook or export jobs.

```
GET /api/admin/dlq?type=webhook|export
POST /api/admin/dlq/replay?type=webhook|export {"id": "..."}
```

The list endpoint returns recent dead letters while the replay endpoint
re-enqueues a selected job for processing.

## CSP Reports

HTML responses include a `Content-Security-Policy-Report-Only` header directing
violation reports to `/csp/report`. The endpoint keeps the last 500 entries in
Redis for 24 hours with any `token` query parameters redacted and exposes them
for inspection via:

```
GET /admin/csp/reports
```

## Test Alert

Verify paging paths by emitting a synthetic alert:

```bash
python scripts/emit_test_alert.py --message "Test alert"
```

This should trigger a Slack message in `#ops` and an email to
`ops@example.com`. Scheduled GitHub Actions jobs send this once a month
against both production and staging to ensure the route stays healthy.


## Stock vs KOT Reconciliation

Flag significant mismatches between reported stock and kitchen order tickets.

```bash
python scripts/stock_kot_reconcile.py --csv report.csv --threshold 5
```

The CSV requires `item`, `sold_qty`, `KOT_cnt` and `variance` columns. Rows with
an absolute variance above the threshold trigger an email to `OPS_EMAIL`. SMTP
settings are read from `SMTP_HOST`, `SMTP_PORT` and optional `SMTP_USER`/`SMTP_PASS`.

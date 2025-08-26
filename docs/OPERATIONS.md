# Operations

## Status Endpoint

External monitors can poll `GET /status.json` to observe platform health. The file contains a top-level `state` (`operational` or `degraded`) and a list of active `incidents`.
Use the helper script to start or resolve incidents:

```
python ops/scripts/status_page.py start "<title>" "<details>"
python ops/scripts/status_page.py resolve "<title>"
```

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

## L1 Support Console

Operations staff can perform safe remediation actions via a minimal support console. The API exposes:

```
GET /admin/support/console/search?tenant=<id>&table=<code>&order=<id>
POST /admin/support/console/order/{order_id}/resend_invoice
POST /admin/support/console/order/{order_id}/reprint_kot
POST /admin/support/console/order/{order_id}/replay_webhook
POST /admin/support/console/staff/{staff_id}/unlock_pin
```

All endpoints require a `super_admin` role. Requests lacking this role return:

```json
HTTP 403
{"ok": false, "error": {"code": 403, "message": "forbidden"}}
```

The `search` endpoint requires a `tenant` parameter and restricts lookups to
that tenant. If the tenant does not exist, the server responds with:

```json
HTTP 404
{"ok": false, "error": {"code": 404, "message": "tenant not found"}}
```

Successful operations return data wrapped in an `ok` envelope. Example:

```json
{
  "ok": true,
  "data": {
    "tenant": {"id": "...", "name": "..."},
    "table": {"id": "...", "code": "T1"},
    "order": {"id": 1, "status": "READY"}
  }
}
```

Unsuccessful operations are not audit logged.

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
python scripts/stock_kot_reconcile.py --csv report.csv --threshold 5 [--verbose]
```

The CSV requires `item`, `sold_qty`, `KOT_cnt` and `variance` columns. Rows with
an absolute variance above the threshold trigger an email to `OPS_EMAIL`. SMTP
settings are read from `SMTP_HOST`, `SMTP_PORT` and optional `SMTP_USER`/`SMTP_PASS`.
Provide `SMTP_FROM` to override the sender address. Use `--verbose` to enable
debug logging; invalid or incomplete rows are skipped with warnings.

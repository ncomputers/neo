# Data Retention

The platform supports per-tenant data retention. Old guest PII is anonymised and
orders beyond the retention window are removed.

## CLI

```
python scripts/purge_data.py --tenant TENANT_ID --days N
```

Purges data for the given tenant, anonymising guest details and deleting orders
older than `N` days.

## Admin API

* `POST /api/admin/retention/preview` – return counts of rows that would be
  affected. Body: `{ "tenant": "TENANT_ID", "days": 30 }`
* `POST /api/admin/retention/apply` – apply the purge and log an audit entry.

Both routes require a `super_admin` token.

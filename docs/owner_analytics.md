# Owner Analytics

The `scripts/owner_analytics.py` helper computes owner activation and retention
metrics across all outlets. It aggregates:

- **Activation** – counts of owners placing their first order on day 0, within 7
  days and within 30 days of onboarding.
- **Retention** – owners returning 7 and 30 days after their first order.
- **Active outlets** and **average orders per outlet** for each day.

To generate a 30‑day report locally:

```bash
python scripts/owner_analytics.py --days 30
```

An API endpoint is also available for dashboards:

```
GET /api/admin/analytics/owners?range=30
```

The optional ``range`` parameter accepts 7, 30 or 90 days and defaults to 30.
It returns a time‑series payload exposing D0/D7/D30 retention counts, active
outlets and average orders per outlet. Results are cached for ten minutes and
require a ``super_admin`` role bearer token.

## Multi‑outlet summary

Owners may aggregate performance across specific outlets:

```
GET /api/analytics/outlets?ids=t1,t2&from=YYYY-MM-DD&to=YYYY-MM-DD
```

The response includes combined orders, sales, average order value, top items,
median preparation time (prep SLA) and a ``voids_pct`` representing the
percentage of orders cancelled during the period.

The ``x-tenant-ids`` header defines the tenant scope. All ``ids`` in the query
string must be within this scope or a ``403`` will be returned. The ``from`` and
``to`` dates are inclusive.

A sample payload:

```json
{
  "orders": 42,
  "sales": 1234.0,
  "aov": 29.38,
  "top_items": [{"name": "Veg Item", "qty": 10}],
  "median_prep": 300.0,
  "voids_pct": 5.0
}
```

Appending ``export=csv`` streams a CSV export with per‑outlet rows, including
the ``voids_pct`` column. The response yields the header followed by one line
per outlet so large exports do not need to be buffered in memory.

Example request:

```bash
curl "https://example.com/api/analytics/outlets?ids=t1,t2&from=2024-01-01&to=2024-01-03&export=csv" \
  -H "x-tenant-ids: t1,t2"
```


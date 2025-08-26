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

The response includes combined orders, sales, average order value, top items
and median preparation time for the selected outlets. Adding ``format=csv``
returns a CSV export with per‑outlet metrics.

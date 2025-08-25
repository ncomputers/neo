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
GET /api/admin/analytics/owners
```

It returns a time‑series payload mirroring the CLI output and requires a
`super_admin` role bearer token.

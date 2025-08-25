# Dashboard Routes

Owner dashboard endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant}/dashboard/charts?range=7\|30\|90 | Daily sales, orders, average ticket, 7/30-day sales moving averages, hourly sales heatmap, payment mix and anomaly flags for the selected range. Cached for 5 minutes (use `force=true` to bypass). |

# Dashboard Routes

Owner dashboard endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant}/dashboard/charts?range=7\|30\|90 | Daily sales, orders, average ticket and payment mix for the selected range. Cached for 5 minutes (use `force=true` to bypass). |

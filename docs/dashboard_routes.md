# Dashboard Routes

Owner dashboard endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant}/dashboard/charts?range=7\|30\|90 | Daily sales, orders, average ticket, 7/30-day sales moving averages, hourly sales heatmap, payment mix and anomaly flags for the selected range. Cached for 5 minutes (use `force=true` to bypass). |

Charts pull from the `sales_rollup` table for precomputed daily totals and
fall back to live aggregation when a day's rollup is missing. The
`scripts/rollup_daily.py` job recomputes yesterday and today's rollups hourly.
It uses a Redis lock (`rollup:{tenant}:{date}`) to avoid double runs and emits
Prometheus counters `rollup_runs_total` and `rollup_failures_total`.
`scripts/rollup_daily.py` job recomputes yesterday and today's rollups hourly,
uses a Redis lock (`rollup:{tenant}:{date}`) to avoid double execution and
exposes `rollup_runs_total`/`rollup_failures_total` Prometheus counters.

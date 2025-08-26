# Query Plan Regression Guard

The `scripts/plan_guard.py` utility protects against performance regressions in
critical SQL queries. It executes each query with `EXPLAIN (ANALYZE, BUFFERS)`
multiple times, computes the 95th percentile (p95) execution time and compares it
with a stored baseline. CI fails when the measured p95 exceeds 120% of the
baseline.

## Usage

```bash
python scripts/plan_guard.py --dsn $DATABASE_URL --baseline scripts/plan_baseline.json
```

The baseline file maps query names to their SQL and expected p95 in
milliseconds. Update the baseline after intentional performance improvements.

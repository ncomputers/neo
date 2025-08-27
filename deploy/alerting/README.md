# Error Budget Burn Alerts

Prometheus alert rules for monitoring error budget burn rates. The rules in
[`error_budget.yml`](error_budget.yml) cover the following routes:

- Guest order
- KDS
- Billing/checkout

Alerts fire when a route consumes a significant portion of its error budget:

| Window | Burn rate | Severity |
| ------ | --------- | -------- |
| 1h     | >10%      | warning  |
| 6h     | >20%      | page     |
| 24h    | >40%      | SEV2     |

Copy `error_budget.yml` into the directory where Prometheus loads rule files and
reload Prometheus to apply the alerts.

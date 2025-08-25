# Prometheus Alerts

Default alerting rules for the Neo stack are provided in [`prometheus-alerts.yml`](prometheus-alerts.yml).

## Wiring

1. Copy `prometheus-alerts.yml` into the directory where Prometheus loads rule files, e.g. `/etc/prometheus/rules/`.
2. Reference the file from your `prometheus.yml`:
   ```yaml
   rule_files:
     - /etc/prometheus/rules/prometheus-alerts.yml
   ```
3. Reload Prometheus so the new rules take effect (`systemctl reload prometheus` or `kill -HUP`).
4. Ensure Alertmanager is configured to handle fired alerts.

The rules cover API errors and latency, worker backlog, missed tenant digests, and database or Redis outages.

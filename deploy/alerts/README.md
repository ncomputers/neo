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

### Alertmanager Templates

Subject and body templates for common alerts are available in [`templates.tmpl`](templates.tmpl).

To use them:

1. Copy `templates.tmpl` into the directory where Alertmanager loads templates, e.g. `/etc/alertmanager/templates/`.
2. Reference the file from your `alertmanager.yml`:
   ```yaml
   templates:
     - /etc/alertmanager/templates/templates.tmpl

   receivers:
     - name: ops-email
       email_configs:
         - to: ops@example.com
           subject: '{{ template (printf "%s.subject" .CommonLabels.alertname) . }}'
           html: '{{ template (printf "%s.body" .CommonLabels.alertname) . }}'
   ```
3. Reload Alertmanager so the new templates are picked up.

The rules cover API errors and latency, worker backlog, missed tenant digests, and database or Redis outages.

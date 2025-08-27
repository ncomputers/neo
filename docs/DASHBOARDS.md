# Dashboards

`deploy/dashboards/export_pack.json` bundles common Grafana dashboards:

- Pilot telemetry
- SLO/SLA
- RUM
- KDS queue age
- Error budget
- Webhook breaker

## Importing

1. Open Grafana and go to **Dashboards → Import**.
2. Upload `export_pack.json` or paste its contents.
3. Select a data source and folder.
4. Click **Import** to load the dashboards.

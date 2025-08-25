# Grafana Dashboards

This directory contains out-of-the-box dashboards for monitoring the platform.

## Dashboards

- `api-overview.json` – request rate, error rate and latency for API services.
- `workers-overview.json` – job throughput and failures for background workers.
- `tenants-kpi.json` – tenant sales, orders and ticket size over 7/30/90 days.

## Importing

1. Open Grafana and go to **Dashboards → New → Import**.
2. Upload one of the JSON files from this folder or paste its contents.
3. When prompted, select the Prometheus data source.

## Variables

Each dashboard defines variables that must be set after import:

- **datasource** – select the Prometheus data source.
- **service** – API service label for `api-overview`.
- **worker** – worker label for `workers-overview`.
- **tenant** – tenant label for `tenants-kpi`.
- **period** – choose `7d`, `30d` or `90d` for KPI calculations.

Variables appear at the top of the dashboard. Adjust them to filter metrics for your environment.

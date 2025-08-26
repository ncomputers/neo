# Load Testing

This directory contains [Locust](https://locust.io/) scenarios for the guest flow with locked performance targets:

- **Scan → Menu** – `GET /g/{table_token}/menu` p95 < 200 ms.
- **Add → Place Order** – `POST /g/{table_token}/order` p95 < 400 ms.
- **Table Map SSE** – maintain 1 000 clients per outlet via `/api/outlet/{tenant}/tables/map/stream`.

The run fails if the p95 thresholds are exceeded.

## Usage

Set the target host in `HOST` and optionally override `TABLE_TOKEN` and `TENANT`:

```bash
export HOST="http://localhost:8000"
export TABLE_TOKEN="T-001"
export TENANT="demo"
locust --headless -f load/locustfile.py -u 10 -r 10 -t 1m
```

The script spawns virtual users that perform the above actions against the configured host.

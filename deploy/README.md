# Deployment

Example steps to run Neo behind systemd and nginx on a Linux host.
## Helm chart

A Helm chart for Kubernetes deployments lives in [helm](helm/README.md).


## 1. Install dependencies
- Python 3.12+
- `uvicorn` and project requirements: `pip install -r api/requirements.txt`
- nginx and systemd (usually preinstalled on most distributions)

## 2. Set up the application
```bash
# place the code somewhere, e.g.
sudo mkdir -p /srv/neo
sudo chown $USER /srv/neo
cp -r . /srv/neo
```
Create an environment file with the required variables:
```bash
sudo mkdir -p /etc/neo
sudo nano /etc/neo/neo-api.env
```

The API can route read-heavy requests to a replica database by setting
`READ_REPLICA_URL`. During startup the replica is health‑checked and the
primary is used automatically if the replica is unreachable.

## 3. systemd service
```bash
sudo cp deploy/systemd/neo-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neo-api
```
This starts Uvicorn on `127.0.0.1:8000` and restarts it automatically on failure.

## 4. nginx reverse proxy
```bash
sudo cp deploy/nginx/neo.conf /etc/nginx/sites-available/neo.conf
sudo ln -s /etc/nginx/sites-available/neo.conf /etc/nginx/sites-enabled/
# obtain TLS certificates via certbot or other means
sudo nginx -t && sudo systemctl reload nginx
```
The configuration enables TLS, gzip compression and proper headers for
WebSockets and Server‑Sent Events with 60 s timeouts.

After these steps the API should be available at `https://example.com`.

## 5. Synthetic canary probe
A lightweight canary places and settles a small order, verifies KOT and invoice PDF generation, exercises the checkout flow and triggers the daily digest endpoint. Install the service and timer:

```bash
sudo cp deploy/systemd/neo-canary.service /etc/systemd/system/
sudo cp deploy/systemd/neo-canary.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neo-canary.timer
```

The probe runs every 10 minutes and logs success or failure.

## 6. Enable rollup
Recompute sales rollups hourly to keep analytics current. Install the service and timer:

```bash
sudo cp deploy/systemd/neo-rollup.service /etc/systemd/system/
sudo cp deploy/systemd/neo-rollup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neo-rollup.timer
```


## 7. Retention enforcement
Run the data retention helper daily for all tenants. Install the service and timer:

```bash
sudo cp deploy/systemd/neo-retention.service /etc/systemd/system/
sudo cp deploy/systemd/neo-retention.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neo-retention.timer
```

## 8. Grace/expiry reminders
Send renewal nudges as licenses approach expiry or during the grace window. Install the service and timer:

```bash
sudo cp deploy/systemd/neo-grace.service /etc/systemd/system/
sudo cp deploy/systemd/neo-grace.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neo-grace.timer
```

## 9. Blue/green releases
For safer deploys that avoid downtime, see the [blue/green guide](bluegreen/README.md)
for instructions on upstream swaps, health gates and release smoke tests.
## Grafana dashboards

Prebuilt dashboards for API, background workers and tenant KPIs are located in
[`deploy/grafana`](grafana/README.md). Import them into Grafana to get instant
metrics visibility.


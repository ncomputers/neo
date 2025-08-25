# Blue/green deployment

A minimal guide for releasing Neo using the blue/green pattern.

## 1. Nginx upstream swap
Deploy a new stack (green) alongside the current one (blue). Once the green
instance is ready, repoint Nginx to it by updating the upstream block and
reloading the proxy:

```bash
sudo sed -e 's/upstream blue/upstream green/' -i /etc/nginx/sites-available/neo.conf
sudo nginx -t && sudo systemctl reload nginx
```

## 2. Health gates
Before and after the swap, gate traffic on the `/ready` endpoint until it
returns HTTP 200. This ensures the application has completed migrations and
warmed caches.

```bash
curl -f https://example.com/ready
```

## 3. Smoke suite
Run a tiny canary order to confirm end‑to‑end functionality. The helper script
places and then voids an order:

```bash
python scripts/smoke_release.py --tenant TENANT --table TABLE
```

If the script exits with code 0 the release is considered healthy.

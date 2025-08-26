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

## Weighted ramp
Instead of an instant flip you can gradually shift traffic using Nginx
weights. The helper below bumps the new stack from 5% to 25% to 50%, verifying
`/ready` after each change:

```bash
python scripts/weighted_ramp.py --new neo-green --old neo-blue --base-url https://example.com
```

For an option that renders the upstream from a template and automatically
rolls back if a health check fails, use the canary helper:

```bash
python scripts/weighted_canary_ramp.py --new neo-green --old neo-blue --base-url https://example.com
```

## 2. Health gates
Before and after the swap, gate traffic on the `/preflight` and `/ready`
endpoints until both return HTTP 200. This ensures the application has completed
migrations and warmed caches.

```bash
curl -f https://example.com/preflight
curl -f https://example.com/ready
```

## 3. Smoke suite
Run a minimal synthetic order to confirm end‑to‑end functionality:

```bash
python scripts/canary_probe.py --minimal --tenant TENANT --table TABLE
```

If the script fails, stop the new instance to roll back.

## 4. Canary probe
Perform a full synthetic canary round‑trip which also exercises KOT generation
and the digest endpoint:

```bash
python scripts/canary_probe.py --tenant TENANT --table TABLE
```

The probe exits non‑zero on failure and should block the release pipeline.

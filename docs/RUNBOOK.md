# Pilot Operations Runbook

## Start / Stop
- `docker-compose up -d` starts API, worker and web assets
- `docker-compose down` stops all services

## Blue / Green Rollout
1. Build images for the new release
2. Deploy using `scripts/rollout_blue_green.py` with the target color
3. Verify health and switch traffic

## Rollback
- `python scripts/rollback_blue_green.py` restores the previous color
- Confirm metrics and user flows before marking incident resolved

## CDN Invalidation
- Purge cached assets via `scripts/deploy_assetlinks.sh --purge`
- For manual purge hit the CDN provider console with the tenant domain

## Logs & Metrics
- Application logs: `/var/log/neo/*.log`
- Metrics dashboard: `https://grafana.example.com`
- Access logs: cloud provider "load balancer" panel

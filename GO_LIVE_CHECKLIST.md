# Go Live Checklist

- [ ] Ensure all migrations are applied
- [ ] Verify service health and metrics
- [ ] Announce release to stakeholders
- [ ] Run pilot rollout
    - `python scripts/release_tag.py --rc`
    - `python scripts/deploy_blue_green.py --env=staging`
    - `python scripts/weighted_canary_ramp.py --env=staging`
    - `python scripts/canary_probe.py --env=staging`
    - enable telemetry/NPS flags

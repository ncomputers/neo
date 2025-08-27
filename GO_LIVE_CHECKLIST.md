# Go Live Checklist

- [ ] Ensure all migrations are applied
- [ ] Verify service health and metrics
- [ ] Announce release to stakeholders
- [ ] Run pilot rollout
    - `make pilot`
    - enable telemetry/NPS flags
- [ ] Tag GA release
    - `make release-ga`
- [ ] Run production rollout
    - `make prod`

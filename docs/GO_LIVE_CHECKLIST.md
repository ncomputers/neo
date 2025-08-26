# Go-Live Checklist

## Pilot readiness

- DNS entries created; resolve to pilot stack
- SSL certificates valid; auto-renew scheduled
- Preflight API = OK
- DB/Redis healthy; migrations applied
- Backups recent; restore drill pass
- Alerts firing; dashboards visible
- Pilot smoke: menu→order→bill path OK
- Printing agent OK; fonts verified
- Licensing plan + grace flows verified
- Telemetry and NPS capture enabled ([pilot survey](PILOT_SURVEY.md))

## General availability

- DNS cutover plan approved
- SSL certs deployed on GA domain
- Canary release toggled; metrics healthy
- Blue/green switch rehearsed
- Rollback path documented and tested
- Alert routing to on-call channels confirmed
- Telemetry dashboards verified ([analytics](analytics.md))
- Rollback status documented with reference to [status.json](../status.json)

# Incident Runbook

## SEV Levels
- **SEV0** – Complete outage or critical data loss. Immediate, all hands response.
- **SEV1** – Major functional loss impacting many tenants; no workaround.
- **SEV2** – Partial degradation with limited workaround for some tenants.
- **SEV3** – Minor functionality issue or bug with available workaround.
- **SEV4** – Informational issue or monitoring alert requiring follow up.

## Roles
- **Incident Commander** – leads response and decision making.
- **Communications Lead** – updates stakeholders and status channels.
- **Operations Engineer** – troubleshoots and restores service.
- **Scribe** – records timeline and actions for postmortem.

## Communication Template
```
[SEV{level}] {summary}
Start: {timestamp}
Status: {current status}
Next Update: {next update time}
Contact: {incident commander}
```

## Rollback Steps
1. Identify last known good version.
2. Trigger rollback in deployment pipeline.
3. Monitor metrics and logs for recovery.
4. Announce resolution and close incident.

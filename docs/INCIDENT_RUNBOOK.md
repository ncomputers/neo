# Incident Runbook

## Severity Ladder

| SEV | Impact | Communication |
| --- | ------ | ------------- |
| **SEV0** | Complete outage or critical data loss. | Page on-call immediately, open incident bridge, notify leadership, and update Status Page and #incidents every 15 min. |
| **SEV1** | Major functional loss impacting many tenants; no workaround. | Page on-call, update #incidents and Status Page every 30 min. |
| **SEV2** | Partial degradation with limited workaround for some tenants. | Notify #ops channel and provide updates hourly. |
| **SEV3** | Minor functionality issue with available workaround. | Discuss asynchronously in #ops and include in daily summary. |
| **SEV4** | Informational issue or monitoring alert requiring follow up. | Log for follow-up; no real-time comms. |

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

## Testing
Use `scripts/emit_test_alert.py` to trigger a synthetic alert during drills.

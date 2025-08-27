# Incident Communication Templates

Use these templates to keep stakeholders informed during service incidents.

## Initial Announcement
**Subject:** Incident Detected

Hi team,

We are investigating an ongoing incident affecting <impacted_service>. Updates will be posted in the incident channel and on the status page. Next update in 30 minutes.

Thanks,
Ops

## Progress Update
**Subject:** Incident Update

Hi team,

We continue to work on the incident affecting <impacted_service>. Current status: <current_status>. Next update in 30 minutes.

Thanks,
Ops

## Resolution
**Subject:** Incident Resolved

Hi team,

The incident affecting <impacted_service> has been resolved as of <time>. Systems are back to normal. Please report any lingering issues.

Thanks,
Ops

---

During a SEV, `/status.json` is backed by Redis and reflects the current `state` and any active incidents so external systems can track progress.
Valid values for `state` include `ok`, `degraded`, and `outage`.

Start an incident and mark the status page as degraded:

```
python ops/scripts/status_page.py start "<title>" "<details>"
```

Resolve an incident and restore the status page when all issues are cleared:

```
python ops/scripts/status_page.py resolve "<title>"
```

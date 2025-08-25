# Incident Response Runbook

## Common failures
- Order service timeout or degraded performance
- Database connection errors
- Queue backlog causing delayed notifications

## Dashboards to check
- API latency and error-rate dashboard
- Database health dashboard
- Worker queue depth dashboard

## SLIs
- Request success rate
- P95 latency
- Queue processing time

## Rollback steps
1. Identify the offending deployment version
2. Trigger rollback via the deployment pipeline
3. Verify services stabilize and metrics recover

## Communications template
```
**Incident**: <summary>
**Impact**: <what users experience>
**Timeline**:
- Start: <timestamp>
- Resolution: <timestamp>
**Root cause**: <cause>
**Mitigation**: <actions taken>
**Next steps**: <follow-up tasks>
```

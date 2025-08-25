# Launch Plan

## Timeline
| Week | Milestone |
|------|-----------|
| 1 | enable pilot in staging |
| 2 | onboard first outlet |
| 3 | expand to remaining pilots |
| 4 | general availability decision |


## Owners
| Area | Owner(s) |
|------|------------------------|
| Product | Dana (PM) |
| Engineering | Ravi (backend), Mei (frontend) |
| Operations | Luis |

## Rollback
1. **Trigger:** error rate >5% or critical bug
2. **Steps:**
   - disable feature flag
   - redeploy previous tag
   - notify stakeholders
3. **Postmortem:** document root cause and prevention actions


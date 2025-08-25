# Launch Plan

## Timeline
| Week | Milestone |
|------|-----------|
| 1 | Enable pilot in staging |
| 2 | Onboard first outlet |
| 3 | Expand to remaining pilots |
| 4 | General availability decision |

## Owners
| Area | Owner(s) |
|------|------------------------|
| Product | Dana (PM) |
| Engineering | Ravi (backend), Mei (frontend) |
| Operations | Luis |

## Rollback
1. **Trigger:** error rate >5% or critical bug
2. **Steps:**
   - Disable feature flag
   - Redeploy previous tag
   - Notify stakeholders
3. **Postmortem:** document root cause and preventive actions


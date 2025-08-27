# Rollback Drill

A quick exercise to keep rollback muscle memory fresh.

## 10-minute drill

1. **Identify previous tag** (1 min)
   - Use deploy logs or `git tag` to find the last known-good release.
2. **Execute rollback** (2 min)
   ```bash
   python scripts/rollback_blue_green.py --env=prod --to=<prev_tag>
   ```
3. **Watch the rollout** (5 min)
   - The script runs `kubectl` to shift traffic and waits for the deployment to stabilise.
4. **Verify service** (2 min)
   - Hit critical endpoints or run smoke tests to confirm the old version works.

A GitHub Actions workflow performs a weekly dry-run against staging so the team
practises these steps regularly.

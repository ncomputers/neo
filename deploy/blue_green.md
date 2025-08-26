# Blue/green rollouts

The `scripts/weighted_canary_ramp.py` helper gradually shifts traffic from the
existing stack (blue) to a new stack (green).

```bash
python scripts/weighted_canary_ramp.py --new neo-green --old neo-blue --base-url https://example.com
```

Traffic is ramped 5% → 25% → 50% → 100%. After each step the script checks
`/ready` and verifies error budgets via `/admin/ops/slo`. Any health check
failure or error budget burn aborts the rollout and restores 100% of traffic to
the old stack.

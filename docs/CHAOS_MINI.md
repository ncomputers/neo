# Mini Chaos Drills

Lightweight script to exercise core resiliency paths on staging.

## What it does

`scripts/chaos_mini.py` runs three short experiments:

1. **Read replica failover** – flips `READ_REPLICA_URL` to an invalid host for 60s while polling the app's health endpoint to ensure it falls back to the primary database.
2. **Redis timeout** – issues a `CLIENT PAUSE` for 30s and then pushes/pops a test message to confirm the queue recovers.
3. **Printer agent outage** – sends a kitchen order ticket to an unreachable printer for 60s and verifies it prints once the printer URL is restored.

## Running on staging

```bash
export APP_HEALTH_URL="https://staging.example.com/health"
export REDIS_URL="redis://staging-redis:6379/0"
export PRINTER_URL="https://staging-printer.example.com/kot"
python scripts/chaos_mini.py
```

The script only mutates local environment variables and sleeps between checks. Run during a low-traffic window and abort with `Ctrl+C` if needed.

For experiments triggered during drills, aggregate exposure and conversion stats using `GET /exp/ab/report`.

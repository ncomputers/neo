# GameDay Fault Injection

Periodic drills ensure we can detect and recover from common failure modes
in staging. Scenarios are executed via `scripts/gameday_inject.py` either
manually or from CI.

## Running locally

```bash
python scripts/gameday_inject.py --scenario kds_offline --dry-run
```

Pass multiple `--scenario` flags to run several drills. The `--dry-run` flag
skips destructive toggles and is recommended outside staging.

## Safety guards

* Scenarios auto‑revert on exit.
* Each run writes a result JSON with timings and success flags.
* The script retries once before failing.

## Rollback

If a drill misbehaves, execute the script with the same scenario and the
`--dry-run` flag which restores environment variables. Most actions also
revert after a short timeout.

## On‑call

Operational issues should be escalated to the platform on‑call engineer
listed in `ops/oncall.md`.

## Abort

To abort all running drills, send SIGINT (Ctrl‑C); the script catches the
signal and reverts in‑progress scenarios. Auto‑revert windows are capped at
2 minutes.

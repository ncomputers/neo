# Billing Dunning

The scheduler sends renewal reminders to outlet owners before and after subscription expiry.

## Cadence

| When | Template key | Description |
| --- | --- | --- |
| 7 days before expiry | `T-7` | Heads up |
| 3 days before expiry | `T-3` | Action recommended |
| 1 day before expiry | `T-1` | Last day |
| Day of expiry | `T+0` | Expired |
| 3 days after expiry | `T+3` | Still in grace |
| 7 days after expiry | `T+7` | Grace ends today |

## Merge fields

`{name}`, `{outlet}`, `{plan}`, `{renew_url}`, `{days_left}`

## Opt-out

Tenants may disable email or WhatsApp reminders via admin controls.

## Manual run

```
python scripts/dunning_scheduler.py
```

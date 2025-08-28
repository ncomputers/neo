# Billing Dunning

This document outlines the cadence and controls for subscription renewal reminders.

## Cadence

| Key | When |
| --- | --- |
| T-7 | 7 days before expiry |
| T-3 | 3 days before expiry |
| T-1 | 1 day before expiry |
| T+0 | On the day of expiry |
| T+3 | 3 days into grace |
| T+7 | 7 days into grace |

## Merge Fields

Templates support `{name}`, `{outlet}`, `{plan}`, `{renew_url}`, `{days_left}`.

## Opt-out

Tenants may opt out per channel. Snoozing hides in-app banners until midnight.

## Manual Run

```bash
python scripts/dunning_scheduler.py
```

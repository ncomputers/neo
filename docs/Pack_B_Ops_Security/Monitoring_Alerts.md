# Monitoring & Alerts

## Health
- Heartbeat from local nodes (every 60s). Alert after 5 missed beats.
- API liveness & readiness probes.
- Disk space thresholds for Postgres & MinIO.

## Event Alerts (rule-based)
- new_order, bill_ready, payment_received, day_close, device_offline, subscription_expiring.
- Channels: Email (default), WhatsApp/SMS optional.

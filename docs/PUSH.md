# Web Push Notifications

Guest devices can register for Web Push updates so they are alerted when an
order is ready. Subscriptions are stored in Redis and an outbox event is queued
for delivery. The worker currently stubs the send by logging activity.

## Subscribe

```
POST /api/outlet/{tenant}/push/subscribe?table={code}
{
  "endpoint": "https://example.com/endpoint",
  "keys": {
    "p256dh": "<base64>",
    "auth": "<base64>"
  }
}
```

## Order Ready

When an order transitions to `READY` and a subscription exists for the table,
an outbox item with channel `webpush` is queued. The notification worker logs
`web-push dispatched` when processing this stub event.

## VAPID Keys

Set `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` environment variables to prepare
for real Web Push delivery. The current implementation does not send pushes and
serves only as scaffolding.

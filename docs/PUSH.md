# Web Push Notifications

Guest devices can register for Web Push updates so they are alerted when an
order is ready. Subscriptions are stored in Redis and delivery is currently a
stub that logs activity.

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
a background worker logs `web-push queued`.

## VAPID Keys

Set `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` environment variables to prepare
for real Web Push delivery. The current implementation does not send pushes and
serves only as scaffolding.

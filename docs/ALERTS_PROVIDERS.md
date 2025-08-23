# Alerts Providers

Notification delivery channels are pluggable and resolved at runtime via environment variables.

| Channel | Environment Variable | Default Provider |
|---------|---------------------|------------------|
| WhatsApp | `ALERTS_WHATSAPP_PROVIDER` | `app.providers.whatsapp_stub` |
| SMS | `ALERTS_SMS_PROVIDER` | `app.providers.sms_stub` |

Each provider module must expose a `send(event, payload, target)` function. The worker passes the outbound event record, the payload, and a target value from the rule's configuration.

## Examples

Use the built-in stubs (default):

```bash
export ALERTS_WHATSAPP_PROVIDER=app.providers.whatsapp_stub
export ALERTS_SMS_PROVIDER=app.providers.sms_stub
```

Swap to custom providers:

```bash
export ALERTS_WHATSAPP_PROVIDER=myapp.providers.twilio_whatsapp
export ALERTS_SMS_PROVIDER=myapp.providers.twilio_sms
```

## Webhook Signing

The notification worker signs outbound webhook requests when `WEBHOOK_SIGNING_SECRET` is set. Each request includes:

- `X-Webhook-Timestamp`: UNIX timestamp in seconds.
- `X-Webhook-Signature`: `sha256=` followed by an HMAC-SHA256 digest of `timestamp.body` using the shared secret.

### Verifier pseudocode

```python
import hmac, hashlib, time

def verify(secret: str, body: str, headers: dict, redis):
    ts = headers.get("X-Webhook-Timestamp", "")
    sig = headers.get("X-Webhook-Signature", "")
    expected = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False  # invalid signature
    if abs(time.time() - int(ts)) > 300:
        return False  # stale timestamp
    nonce = f"{ts}.{expected.split('=', 1)[1]}"
    if redis.get(nonce):
        return False  # replayed request
    redis.setex(nonce, 300, 1)
    return True
```

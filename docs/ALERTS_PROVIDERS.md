# Alerts Providers

Notification delivery channels are pluggable and resolved at runtime via environment variables.

| Channel | Environment Variable | Default Provider |
|---------|---------------------|------------------|
| WhatsApp | `ALERTS_WHATSAPP_PROVIDER` | `app.providers.whatsapp_stub` |
| SMS | `ALERTS_SMS_PROVIDER` | `app.providers.sms_stub` |
| Email | `ALERTS_EMAIL_PROVIDER` | `app.providers.email_stub` |
| Slack | `ALERTS_SLACK_PROVIDER` | `app.providers.slack_stub` |

Each provider module must expose a `send(event, payload, target)` function. The worker passes the outbound event record, the payload, and a target value from the rule's configuration.

## Examples

Use the built-in stubs (default):

```bash
export ALERTS_WHATSAPP_PROVIDER=app.providers.whatsapp_stub
export ALERTS_SMS_PROVIDER=app.providers.sms_stub
export ALERTS_EMAIL_PROVIDER=app.providers.email_stub
export ALERTS_SLACK_PROVIDER=app.providers.slack_stub
```

Swap to custom providers:

```bash
export ALERTS_WHATSAPP_PROVIDER=myapp.providers.twilio_whatsapp
export ALERTS_SMS_PROVIDER=myapp.providers.twilio_sms
export ALERTS_EMAIL_PROVIDER=myapp.providers.sendgrid_email
export ALERTS_SLACK_PROVIDER=myapp.providers.slack_api
```

## Slack

The default Slack stub sends `text` payloads to the webhook URL specified by
the `SLACK_WEBHOOK_URL` environment variable.

## Webhook Targets

Creating an alert rule with `channel` set to `webhook` triggers a probe of the
target URL. The API captures TLS details, HTTP status codes and latency
percentiles and checks the destination against the webhook IP allowlist.
Use `/admin/webhooks/probe` to preflight URLs and store these reports. Any
warnings (slow, invalid status, self-signed or blocked IPs) are surfaced during
registration.

## Webhook Signing

The notification worker signs outbound webhook requests when `WEBHOOK_SIGNING_SECRET` is set.

### HMAC Headers

Each request includes:

- `X-Webhook-Timestamp`: UNIX timestamp in seconds.
- `X-Webhook-Signature`: `sha256=` followed by an HMAC-SHA256 digest of `timestamp.body` using the shared secret.

### Verify snippets

#### Python

```python
import hmac, hashlib, time

def verify(secret: str, body: bytes, headers: dict, redis):
    ts = int(headers.get("X-Webhook-Timestamp", "0"))
    sig = headers.get("X-Webhook-Signature", "")
    expected_hash = hmac.new(
        secret.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    expected = f"sha256={expected_hash}"
    if not hmac.compare_digest(sig, expected):
        return False  # invalid signature
    if abs(time.time() - ts) > 300:
        return False  # stale timestamp
    nonce_key = f"wh:nonce:{ts}:{expected_hash}"
    if redis.get(nonce_key):
        return False  # replayed request
    redis.setex(nonce_key, 300, 1)
    return True
```

#### JavaScript

```javascript
const crypto = require('crypto');

function verify(secret, body, headers, redis) {
  const ts = parseInt(headers['x-webhook-timestamp'] || '0', 10);
  const sig = headers['x-webhook-signature'] || '';
  const hash = crypto.createHmac('sha256', secret)
                     .update(`${ts}.${body}`)
                     .digest('hex');
  const expected = `sha256=${hash}`;
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) {
    return false;
  }
  if (Math.abs(Date.now() / 1000 - ts) > 300) {
    return false;
  }
  const nonceKey = `wh:nonce:${ts}:${hash}`;
  if (redis.get(nonceKey)) {
    return false;
  }
  redis.setex(nonceKey, 300, '1');
  return true;
}
```

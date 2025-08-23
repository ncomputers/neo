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

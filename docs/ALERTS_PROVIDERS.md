# Alerts Providers

Notification channels are backed by pluggable provider modules. A provider
implements a single function:

```python
from app.providers import base

# provider modules expose this function
def send(event, payload, target) -> None:
    ...
```

The worker selects a provider for each channel using environment variables:

| Channel  | Env var                    | Default module                     |
|----------|---------------------------|------------------------------------|
| whatsapp | `ALERTS_WHATSAPP_PROVIDER` | `app.providers.whatsapp_stub` |
| sms      | `ALERTS_SMS_PROVIDER`      | `app.providers.sms_stub`      |

Example:

```bash
export ALERTS_WHATSAPP_PROVIDER=app.providers.whatsapp_stub
export ALERTS_SMS_PROVIDER=app.providers.sms_stub
```

The bundled stub providers simply log the payload and mark notifications as
sent. They act as placeholders for real integrations.

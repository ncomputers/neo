# Webhook Verification

This runbook outlines how to verify the monitoring webhook used by automated checks.

## Obtain the Webhook URL

Generate an incoming webhook in your chat or monitoring service (e.g. Slack) and copy the full URL.

## Verify the Webhook

Export the webhook and send a test message:

```bash
export WEBHOOK=https://hooks.example.com/endpoint
curl -X POST -H 'Content-Type: application/json' -d '{"text":"test"}' "$WEBHOOK"
```

## Expected Response

A successful request returns a `2xx` status code. A `404` or `410` indicates the URL is invalid or revoked.

## Troubleshooting

- **Connection refused** – check firewall rules or proxy settings.
- **5xx responses** – the remote service is down; retry later.
- **Timeouts** – ensure the URL is reachable from your network.

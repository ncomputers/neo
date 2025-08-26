# Integration Marketplace

The API exposes stub endpoints for managing simple webhook integrations per tenant.

## List available integrations

```
GET /api/outlet/{tenant}/integrations/marketplace
```

Returns available integration types along with sample payloads and connection status.

## Connect an integration

```
POST /api/outlet/{tenant}/integrations/connect
{
  "type": "slack",
  "url": "https://example.com/hook"
}
```

Validates the URL with a probe and stores the configuration for the tenant.

For detailed setup instructions and troubleshooting, see [INTEGRATIONS.md](INTEGRATIONS.md).

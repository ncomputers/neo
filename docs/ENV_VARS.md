# Environment Variables

The application relies on the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_MASTER_URL` | Connection string for the master database. Defaults to a local SQLite file for development. | `sqlite+aiosqlite:///./dev_master.db` |
| `POSTGRES_TENANT_DSN_TEMPLATE` | Template DSN for tenant databases, with `{tenant_id}` placeholder. Defaults to local SQLite files. | `sqlite+aiosqlite:///./tenant_{tenant_id}.db` |
| `POSTGRES_SUPER_URL` (optional) | Superuser connection URL used when creating databases. Not required for SQLite. |  |
| `DEFAULT_TZ` | Default timezone for application processes. | `UTC` |
| `JWT_SECRET` | Secret key used to sign JWT tokens. | `your_jwt_secret_key` |
| `JWKS_URL` (optional) | JWKS endpoint for verifying JWT signatures. | `https://auth.example.com/jwks.json` |
| `REDIS_URL` | URL for Redis instance. | `redis://localhost:6379/0` |
| `ALLOWED_ORIGINS` | Comma-separated list of origins allowed for CORS. Defaults to `*`. | `https://example.com,https://app.com` |
| `BODY_MAX_KB` | Maximum request body size accepted by the API. | `128` |
| `ADMIN_API_ENABLED` | Enables superadmin endpoints when set to `true`. | `false` |
| `SSE_KEEPALIVE_INTERVAL` | Seconds between SSE keepalive comments. | `15` |
| `EXPORT_MAX_ROWS` | Maximum rows included in export files. Defaults to `10000`. | `10000` |
| `VAPID_PUBLIC_KEY` (optional) | Public key for Web Push authentication. | `BASE64_KEY` |
| `VAPID_PRIVATE_KEY` (optional) | Private key for Web Push authentication. | `BASE64_KEY` |
| `WEBHOOK_SIGNING_SECRET` (optional) | Shared secret for signing outbound webhook requests. | `supersecret` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` (optional) | OTLP trace exporter endpoint. Tracing is disabled when unset. | `http://otel-collector:4318/v1/traces` |
| `OTEL_SERVICE_NAME` (optional) | Service name used for OpenTelemetry traces. Defaults to `neo-api`. | `neo-api` |

## JWT/JOSE

- Tokens are signed using the `HS256` algorithm.
- Access tokens expire after 60 minutes.
 - The signing key is provided via `JWT_SECRET` or `JWKS_URL`.

## Redis Channels

The application uses Redis Pub/Sub for real-time features:

- `rt:update:{table_code}` – WebSocket updates for order status per table.
- `rt:table_map:{tenant}` – Server-Sent Events channel for table map updates. Emits
  `event: table_map` messages with heartbeats every 15s and supports the
  `Last-Event-ID` header.


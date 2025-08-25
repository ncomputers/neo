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
| `ENABLE_HSTS` | When set to `1`, adds Strict-Transport-Security header to responses. | `1` |
| `BODY_MAX_KB` | Maximum request body size accepted by the API. | `128` |
| `ADMIN_API_ENABLED` | Enables superadmin endpoints when set to `true`. | `false` |
| `SSE_KEEPALIVE_INTERVAL` | Seconds between SSE keepalive comments. | `15` |
| `MAX_CONN_PER_IP` | Maximum concurrent real-time connections allowed per client IP. | `20` |
| `EXPORT_MAX_ROWS` | Maximum rows included in export files. Defaults to `10000`. | `10000` |
| `VAPID_PUBLIC_KEY` (optional) | Public key for Web Push authentication. | `BASE64_KEY` |
| `VAPID_PRIVATE_KEY` (optional) | Private key for Web Push authentication. | `BASE64_KEY` |
| `WEBHOOK_SIGNING_SECRET` (optional) | Shared secret for signing outbound webhook requests. | `supersecret` |
| `WEBHOOK_ALLOW_HOSTS` | Allowed webhook hostnames (comma, supports `*` wildcard). | `hooks.slack.com,*.example.com` |
| `WEBHOOK_DENY_CIDRS` (optional) | CIDR ranges blocked for webhook egress. | `10.0.0.0/8` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` (optional) | OTLP trace exporter endpoint. Tracing is disabled when unset. | `http://otel-collector:4318/v1/traces` |
| `OTEL_SERVICE_NAME` (optional) | Service name used for OpenTelemetry traces. Defaults to `neo-api`. | `neo-api` |
| `OTEL_SAMPLER_RATIO` (optional) | Sampling ratio between 0 and 1. Defaults to `0.1`. | `0.25` |
| `GIT_SHA` (optional) | Git commit SHA exposed by the `/version` endpoint. | `c0ffee` |
| `BUILT_AT` (optional) | Build timestamp exposed by the `/version` endpoint. | `2024-01-01T00:00:00Z` |
| `ENV` (optional) | Deployment environment (`prod`, `staging`, or `dev`). | `prod` |

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


## Secret Rotation

Use `scripts/rotate_secrets.py` to rotate secrets without downtime. The script manages three suffixes for supported variables:

- `<VAR>_NEXT` – upcoming value used during the dual verification period
- `<VAR>` – active value
- `<VAR>_PREV` – previous value, safe to remove after cutover

Supported kinds:

- `jwt` for `JWT_SECRET`
- `webhook` for `WEBHOOK_SIGNING_SECRET`
- `vapid` for `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`

Example workflow:

```bash
# generate next value(s)
python scripts/rotate_secrets.py prepare jwt

# after propagating, switch over
python scripts/rotate_secrets.py cutover jwt

# once old value is no longer needed
python scripts/rotate_secrets.py purge jwt
```

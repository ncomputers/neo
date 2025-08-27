# Environment Freeze

This document locks down the production environment contract.

## Required Variables

| Variable | Purpose |
|----------|---------|
| `POSTGRES_MASTER_URL` | Master database DSN |
| `POSTGRES_TENANT_DSN_TEMPLATE` | Template DSN for tenant databases |
| `JWT_SECRET` | JWT signing key (or set `JWKS_URL`) |
| `REDIS_URL` | Redis connection URL |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist |
| `ENABLE_HSTS` | `1` to enable strict transport security |
| `BODY_MAX_KB` | Maximum request body size in kilobytes |
| `ADMIN_API_ENABLED` | Enable admin endpoints |
| `SSE_KEEPALIVE_INTERVAL` | Seconds between SSE heartbeats |
| `MAX_CONN_PER_IP` | Max concurrent real-time connections per IP |
| `QUEUE_MAX` | Pending realtime messages before dropping client |
| `EXPORT_MAX_ROWS` | Max rows allowed in export jobs |
| `ENV` | Deployment environment (`prod`) |
| `HEARTBEAT_TIMEOUT_SEC` | WebSocket ping interval and timeout |
| `TENANT_ANALYTICS_ENABLED` | Toggle per-tenant analytics |
| `ANALYTICS_TENANTS` | Comma-separated tenant IDs for analytics |
| `FLAG_SIMPLE_MODIFIERS` | Enable basic menu modifiers |
| `FLAG_WA_ENABLED` | Enable WhatsApp notifications |
| `AB_TESTS_ENABLED` | Enable server-side A/B tests |

## Default Timeouts

- DB slow query warning: 200 ms (`DB_SLOW_QUERY_MS`)
- SSE keepalive: 15 s (`SSE_KEEPALIVE_INTERVAL`)
- WebSocket heartbeat: 30 s (`HEARTBEAT_TIMEOUT_SEC`)

## Queue Sizes

- Realtime message buffer: 100 messages (`QUEUE_MAX`)
- Export row cap: 10 000 rows (`EXPORT_MAX_ROWS`)

## Rate Limits

- Guest traffic: 60 requests/min with burst 100
- Guest POST body cap: 256 KB
- Realtime connections: 20 concurrent per IP (`MAX_CONN_PER_IP`)

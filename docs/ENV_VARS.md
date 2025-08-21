# Environment Variables

The application relies on the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_MASTER_URL` | Connection string for the master database. Defaults to a local SQLite file for development. | `sqlite+aiosqlite:///./dev_master.db` |
| `POSTGRES_TENANT_DSN_TEMPLATE` | Template DSN for tenant databases, with `{tenant_id}` placeholder. Defaults to local SQLite files. | `sqlite+aiosqlite:///./tenant_{tenant_id}.db` |
| `POSTGRES_SUPER_URL` (optional) | Superuser connection URL used when creating databases. Not required for SQLite. |  |
| `DEFAULT_TZ` | Default timezone for application processes. | `UTC` |
| `JWT_SECRET` | Secret key used to sign JWT tokens. | `your_jwt_secret_key` |
| `REDIS_URL` | URL for Redis instance. | `redis://localhost:6379/0` |
| `ALLOWED_ORIGINS` | Comma-separated list of origins allowed for CORS. Defaults to `*`. | `https://example.com,https://app.com` |
| `ADMIN_API_ENABLED` | Enables superadmin endpoints when set to `true`. | `false` |


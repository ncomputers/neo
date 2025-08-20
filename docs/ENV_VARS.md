# Environment Variables

The application relies on the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_MASTER_URL` | Connection string for the master database. | `postgresql://user:pass@localhost/master_db` |
| `POSTGRES_TENANT_DSN_TEMPLATE` | Template DSN for tenant databases, with `{tenant_id}` placeholder. | `postgresql://user:pass@localhost/{tenant_id}_db` |
| `POSTGRES_SUPER_URL` (optional) | Superuser connection URL used when creating databases. | `postgresql://postgres:super@localhost/postgres` |
| `DEFAULT_TZ` | Default timezone for application processes. | `UTC` |
| `JWT_SECRET` | Secret key used to sign JWT tokens. | `your_jwt_secret_key` |
| `REDIS_URL` | URL for Redis instance. | `redis://localhost:6379/0` |


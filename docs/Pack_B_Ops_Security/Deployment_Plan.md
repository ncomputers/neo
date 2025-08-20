# Deployment Plan (Self-host Linux)

## Topology
- Reverse proxy (Caddy/Traefik) → API (FastAPI) → Postgres (master+tenant) → Redis → MinIO.
- Optional local node at outlet (Docker compose) serving LAN when internet down.

## Environments
- staging, prod; both containerized; env via `.env`.

## Steps
1. Provision VM (Ubuntu 22.04 LTS), ports 80/443 open.
2. Install Docker & Compose.
3. Clone repo; set `.env`; `docker compose up -d`.
4. Run migrations (Alembic).
5. Configure domains/subdomains; Caddy obtains SSL automatically.
6. Create super-admin user; onboard first outlet; print QR posters.

## Scale
- API replicas (sticky WS/SSE OK via Redis pub/sub).
- Separate Postgres for master and tenant pools.
- MinIO for assets; S3 external possible.

# Deploy with Docker

This repository provides Docker images for the API service and the background worker. The images share the same base but expose different commands.

Worker images pin the Python base image by digest, upgrade ``setuptools`` during build, and run as a non-root ``app`` user.

## Build images

```bash
docker compose build
```

## Apply database migrations

Run migrations once the database is ready. This uses the Alembic configuration
bundled with the API image and executes them through an async SQLAlchemy engine.

```bash
docker compose run --rm api bash -c "cd api && python -m alembic -c alembic.ini -x db_url=$SYNC_DATABASE_URL upgrade head"
```

## Launch services

```bash
docker compose up -d
```

The compose file starts:

- **api** – FastAPI application served by Uvicorn.
- **worker** – background notification worker.
- **postgres** – PostgreSQL database.
- **redis** – Redis instance for caching and queues.

## Nginx proxy

The `deploy/nginx.conf` file terminates TLS and proxies requests sent to `/api/` to the API container. Mount the file and your TLS certificates into an Nginx container:

```bash
docker run -p 80:80 -p 443:443 \
  -v $(pwd)/deploy/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /path/to/certs:/etc/nginx/certs:ro \
  --network host \
  nginx:alpine
```

Replace `/path/to/certs` with a directory containing `fullchain.pem` and `privkey.pem`.

To trace requests across the proxy and API, forward and log the request ID:

```nginx
proxy_set_header X-Request-ID $request_id;
log_format main '$remote_addr [$time_local] "$request" $status $body_bytes_sent $request_id';
```

The API echoes this header in responses and emits `req_id` in its JSON logs,
allowing easy correlation.

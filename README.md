# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with a `/health` endpoint and Alembic migrations.
- `pwa/` – React + Tailwind front end with a placeholder home page.
- `ops/` – Docker Compose for local development.

## Configuration

Runtime settings are defined in `config.json` and may be overridden by environment variables loaded from a local `.env` file. The `config.py` module exposes a `get_settings()` helper that reads both sources.

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

## API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://localhost:8000/health> to verify the service.

## PWA

```bash
cd pwa
npm install
npm run dev
```

## Docker Compose

```bash
cd ops
docker-compose up --build
```

This stack launches FastAPI, two Postgres databases (master and tenant), Redis, MinIO for S3-compatible storage, and an Nginx reverse proxy.

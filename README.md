# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with a `/health` endpoint and Alembic migrations.
- `pwa/` – React + Tailwind front end with a placeholder home page.
- `ops/` – Operations tooling including Docker Compose for local development.

## Getting Started

### Environment Variables

Copy the example files and adjust as needed:

```bash
cp .env.example .env
cp api/.env.example api/.env
cp pwa/.env.example pwa/.env
cp ops/.env.example ops/.env
```

### API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://localhost:8000/health> to verify the service.

### PWA

```bash
cd pwa
npm install
npm run dev
```

### Docker Compose

```bash
cd ops
cp .env.example .env
docker-compose up --build
```

This stack launches FastAPI, two Postgres databases (master and tenant), Redis, MinIO for S3-compatible storage, and an Nginx reverse proxy.

## CI

GitHub Actions run lint checks for both Python and JavaScript projects.

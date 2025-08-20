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

The API includes a Redis-backed rate limiter that blocks an IP after three consecutive failed requests.

## PWA

```bash
cd pwa
npm install
npm run dev
```

## Docker Compose

From the `ops` directory you can launch the full development stack:

```bash
cd ops
make up
```

The stack includes FastAPI, two Postgres databases (master and tenant), Redis, MinIO for S3-compatible storage, and an Nginx reverse proxy. Shut it down with:

```bash
make down
```

## Tenant Onboarding

Use the helper script to provision a new tenant database and register its
metadata:

```bash
python -c "from api.onboard_tenant import create_tenant; create_tenant('demo', 'demo.local')"
```

The function creates a dedicated Postgres database, applies migrations, and
records branding and configuration details in the master schema.

## Development Notes

Every Python module begins with a filename comment followed by a concise module
docstring. Functions and classes include descriptive docstrings and inline
comments explain non-obvious logic.

Create a virtual environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

Run the full test suite:

```bash
pytest
```

Run a single module or test:

```bash
pytest api/tests/test_auth.py::test_password_login_success
```

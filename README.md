# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with a `/health` endpoint, Alembic migrations, and service helpers such as EMA-based ETA utilities with per-tenant persistence.
- `pwa/` – React + Tailwind front end with a placeholder home page.
- `ops/` – Docker Compose for local development.

## Configuration

Runtime settings are defined in `config.json` and may be overridden by environment variables loaded from a local `.env` file. The `config.py` module exposes a `get_settings()` helper that reads both sources.

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

## Quickstart

The following commands install dependencies, set up the environment, apply
database migrations for both the master schema and an example tenant, and run
the test suite:

```bash
pip install -r api/requirements.txt
python run_all.py --env --install
alembic upgrade head
pytest -q
```

## API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://localhost:8000/health> to verify the service.

All API responses use a standard envelope:

- Success: `{ "ok": true, "data": ... }`
- Error: `{ "ok": false, "error": { "code": ..., "message": ... } }`

### Super Admin

The backend exposes a super-admin endpoint used for tenant provisioning:

- `POST /api/super/outlet` – create an outlet and run tenant migrations. The
  router is present but not yet included in the main application.

### Guest Menu

A guest-facing router exposes menu data for a specific table:

- `GET /g/{table_token}/menu` – list menu categories and items.

This router relies on tenant-specific databases and is not wired into the
application yet.

### Admin Menu

An admin-only route allows toggling item availability:

- `POST /api/outlet/{tenant_id}/menu/item/{item_id}/out_of_stock` – set an
  item's stock flag. Body: `{"flag": true|false}`. Requires an admin role.

### Start Script

Run migrations and launch the API with a single command once dependencies are installed:

```bash
pip install -r api/requirements.txt python-dotenv
python start_app.py
```

The script loads environment variables from `.env`, executes `alembic upgrade head` using `api/alembic.ini` via `python -m alembic`, and starts the application via `uvicorn api.app.main:app`. If Alembic is missing, it will prompt you to install dependencies with `pip install -r api/requirements.txt`.

### Real-time Updates

Connect to `ws://localhost:8000/tables/{id}/ws` to receive live order
notifications. Messages are fanned out via Redis channels named
`rt:update:{table_code}` and include an `eta` field derived from an
exponential moving average of preparation times.
The API includes a Redis-backed rate limiter that blocks an IP after three consecutive failed requests.


### Observability

Each request is tagged with a `correlation_id` that appears in the JSON logs.
All HTTP responses follow a simple envelope structure of
`{"ok": true, "data": ...}` for success or
`{"ok": false, "error": {"code": ..., "message": ...}}` for failures.


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
records branding and configuration details in the master schema. Invoice
numbering for each tenant can be customised via ``invoice_prefix`` and an
``invoice_reset`` policy (``monthly``, ``yearly`` or ``never``).

For development convenience, a lightweight CLI is also available to prepare a
tenant database or schema and report when it's ready:

```bash
python scripts/tenant_create_db.py --tenant TENANT_ID
```

The script will print `READY` once the database is available.

To apply migrations for an existing tenant database, run:

```bash
python scripts/tenant_migrate.py --tenant TENANT_ID
```

To populate a tenant with a minimal category, two items and a table, execute:

```bash
python scripts/tenant_seed.py --tenant TENANT_ID
```

The command prints a JSON payload containing the new record IDs.

## Audit Logging

Login attempts, order edits and payments write to SQLite-backed audit tables.
Run the cleanup helper to purge entries older than the configured retention
period:

```bash
python api/app/audit.py
```

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

## Events

The API emits domain events using a lightweight in-memory Pub/Sub dispatcher. Events
such as `order.placed`, `payment.verified`, and `table.cleaned` are processed by
background consumers for alerting and reporting.

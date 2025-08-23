# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with `/health` and `/ready` endpoints, Alembic migrations, and service helpers such as EMA-based ETA utilities with per-tenant persistence.
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

## Continuous Integration

GitHub Actions runs the test suite and basic lint checks for all pushes and pull
requests.

## API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://localhost:8000/health> for liveness and <http://localhost:8000/ready> for readiness checks.

All API responses use a standard envelope:

- Success: `{ "ok": true, "data": ... }`
- Error: `{ "ok": false, "error": { "code": ..., "message": ... } }`

### Coupons

Coupons can be marked as stackable and may specify a per-invoice `max_discount` cap. When multiple stackable coupons are applied, the invoice `bill_json` records the `applied_coupons` and the combined `effective_discount`.

Attempts to combine a non-stackable coupon with others raise a `CouponError` with code `NON_STACKABLE`.

### Super Admin

The backend exposes a super-admin endpoint used for tenant provisioning:

- `POST /api/super/outlet` – create an outlet and run tenant migrations. The
  router is present but not yet included in the main application.

### Guest Menu

A guest-facing router exposes menu data for a specific table:

- `GET /g/{table_token}/menu` – list menu categories and items.
- `GET /h/{room_token}/menu` – list menu for hotel rooms.
- `POST /h/{room_token}/order` – place a room service order.
- `POST /h/{room_token}/request/cleaning` – request housekeeping for the room.
- `POST /g/{table_token}/bill` – generate a bill; payload may include an optional `tip` and `coupons` list.


This router relies on tenant-specific databases and is not wired into the
application yet.

### Admin Menu

An admin-only route allows toggling item availability:

- `POST /api/outlet/{tenant_id}/menu/item/{item_id}/out_of_stock` – set an
  item's stock flag. Body: `{"flag": true|false}`. Requires an admin role.

### Dashboard

An owner-facing endpoint exposes key performance indicators for the current day:

- `GET /api/outlet/{tenant_id}/dashboard/tiles?force=true` – returns today's order count, sales total, average ETA seconds, and top items. Metrics are computed in the outlet's timezone and cached for 30s (use `force=true` to bypass cache).

### Staff Login

Outlet staff can authenticate with a numeric PIN to perform protected actions:

- `POST /api/outlet/{tenant}/staff/login` – verify a PIN and receive a short-lived JWT.
- `GET /api/outlet/{tenant}/staff/me` – example protected route requiring the JWT.

### Backups

Trigger a JSON backup of a tenant's database:

- `POST /api/outlet/{tenant_id}/backup` – runs the backup script and returns the
  path to the generated file.

### Daily Exports

Download a ZIP bundle of invoices, payments and per-day totals over a date range:

- `GET /api/outlet/{tenant}/exports/daily?start=YYYY-MM-DD&end=YYYY-MM-DD&limit=10000`
  – returns `invoices.csv`, `payments.csv` and `z-report.csv` plus individual invoice
  PDFs (or HTML when the PDF engine is unavailable). The range is capped at 31 days
  and each CSV includes at most `limit` rows (default 10k).

### GST Reports

Generate monthly GST summaries:

- `GET /api/outlet/{tenant}/reports/gst/monthly?month=YYYY-MM` – returns a CSV
  grouped by HSN with CGST/SGST totals for registered outlets, a single summary
  line for composition, or totals without tax lines for unregistered outlets.

### Housekeeping

Cleaning staff can reset tables after guests settle their bills:

- `POST /api/outlet/{tenant_id}/housekeeping/table/{table_id}/start_clean` – mark a table as being cleaned.
- `POST /api/outlet/{tenant_id}/housekeeping/table/{table_id}/ready` – record cleaning completion and reopen the table.
- `POST /api/outlet/housekeeping/room/{room_id}/start_clean` – mark a room as being cleaned.
- `POST /api/outlet/housekeeping/room/{room_id}/ready` – record cleaning completion and reopen the room.

Tables and rooms transition through states such as `open`, `locked` and `cleaning`; guests are blocked from ordering unless the respective table or room is `open`.


### Alerts

Configure and inspect notification rules:

- `POST /api/outlet/{tenant_id}/alerts/rules` – create a rule (`event`, `channel`, `target`, `enabled`).
- `GET /api/outlet/{tenant_id}/alerts/rules` – list configured rules.
- `GET /api/outlet/{tenant_id}/alerts/outbox?status=queued|delivered` – list recent notifications.

### Table Map

Admins can pin tables on a floor plan and retrieve their states:

- `POST /api/outlet/{tenant_id}/tables/{table_id}/position` – set a table's `x`/`y` coordinates and optional label. Requires an admin role.
- `GET /api/outlet/{tenant_id}/tables/map` – list table positions with their current states.


### Start Script

Run migrations and launch the API with a single command once dependencies are installed:

```bash
pip install -r api/requirements.txt python-dotenv
python start_app.py
```

The script loads environment variables from `.env`, executes `alembic upgrade head` using `api/alembic.ini` via `python -m alembic`, and starts the application via `uvicorn api.app.main:app`. If Alembic is missing, it will prompt you to install dependencies with `pip install -r api/requirements.txt`.

### Notification Worker

Queued notifications can be delivered via a small CLI worker:

```bash
POSTGRES_URL=sqlite:///dev_master.db python scripts/notify_worker.py
```

The worker drains `notifications_outbox` rows and currently supports
`console`, `webhook`, `whatsapp_stub` and `sms_stub` channels. The
`*_stub` channels simply log the payload and are placeholders for future
provider adapters.

### Real-time Updates

Connect to `ws://localhost:8000/tables/{id}/ws` to receive live order
notifications. Messages are fanned out via Redis channels named
`rt:update:{table_code}` and include the `order_id`, current `status` and
an `eta_secs` field. The ETA is computed from an exponential moving
average and decreases with elapsed prep time. It never goes below zero and
hits exactly `0` when an order is `ready` or `served`.
The API includes a Redis-backed rate limiter that blocks an IP after three consecutive failed requests.


### Observability

Each request is tagged with a `correlation_id` that appears in the JSON logs.
All HTTP responses follow a simple envelope structure of
`{"ok": true, "data": ...}` for success or
`{"ok": false, "error": {"code": ..., "message": ...}}` for failures.
Prometheus metrics are exposed at `/metrics`, including counters for HTTP requests, orders created, invoices generated, idempotency key usage, lock denials, and HTTP errors.


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
``invoice_reset`` policy (``monthly``, ``yearly`` or ``never``). With a monthly
reset, numbers include the year and month, e.g. ``INV/2024/02/000001``.

### Invoice PDFs

Invoices can be rendered as PDFs via ``GET /invoice/{invoice_id}/pdf``.
Specify ``?size=80mm`` for thermal receipts or ``?size=A4`` for full pages.
If WeasyPrint is unavailable, the endpoint falls back to returning the
rendered HTML.

### KOT PDFs

Kitchen Order Tickets for counter orders can be printed through
``GET /api/outlet/{tenant}/kot/{order_id}.pdf``. The route returns an 80mm
render suitable for thermal printers and falls back to HTML when PDF
generation is not available.

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

For hotel or counter flows, additional helpers are available to create QR tokens:

```bash
python scripts/tenant_seed_hotel.py --tenant TENANT_ID
python scripts/tenant_seed_counter.py --tenant TENANT_ID
```

To compute daily Z-report totals and enqueue a day-close notification into the
master outbox, run:

```bash
python scripts/day_close.py --tenant TENANT_ID --date YYYY-MM-DD
```

The CLI aggregates invoice figures for the specified date and records a
`dayclose` event for downstream processors.

To prune old tenant audit logs, delivered notifications and access logs, run:

```bash
python scripts/retention_sweep.py --tenant TENANT_ID --days 30
```

The sweep deletes `audit_tenant` rows, delivered `notifications_outbox`
entries and `access_logs` records older than the specified retention window.


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

## Takeaway Counters

The project supports a lightweight takeaway flow powered by QR codes at sales
counters. Guests can scan a counter's QR to browse the menu and place an order.
Staff can mark orders as ready or delivered, which triggers invoice generation
suitable for 80 mm thermal printers. See `docs/counter_takeaway.md` for more
details.

# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with `/health` and `/ready` endpoints, Alembic migrations, and service helpers such as EMA-based ETA utilities with per-tenant persistence.
- `pwa/` – React + Tailwind front end with a placeholder home page.
- `ops/` – Docker Compose for local development.

Invoices support optional FSSAI license details when provided.

## Security

Owner and admin accounts can enable optional TOTP-based two-factor authentication. See [`docs/auth_2fa.md`](docs/auth_2fa.md) for available endpoints.

## Configuration

Runtime settings are defined in `config.json` and may be overridden by environment variables loaded from a local `.env` file. The `config.py` module exposes a `get_settings()` helper that reads both sources.

The configuration includes the `kds_sla_secs` threshold (default 900 seconds)
that determines how long a KDS item may remain `in_progress` before a breach
notification is triggered.

Logging can be tuned via:

- `LOG_LEVEL` – set log verbosity (default `INFO`)
- `LOG_FORMAT` – log output format (`json` or `text`, default `json`)
- `LOG_SAMPLE_GUEST_4XX` – sampling rate for guest 4xx logs (default `0.1`)
- `ERROR_DSN` – optional Sentry-compatible DSN for centralized error reporting
- `MAINTENANCE` – when `1`, only admin routes are served; others return `503 {"code":"MAINTENANCE"}`
- `READ_REPLICA_URL` – optional PostgreSQL DSN for read-only queries. When
  reachable, menu fetch, dashboard charts and export endpoints use this
  replica.

Real-time streams expose additional knobs:

- `MAX_CONN_PER_IP` – cap concurrent SSE/WS connections per client IP (default `20`)
- `HEARTBEAT_TIMEOUT_SEC` – seconds between WebSocket pings and heartbeat timeout (default `30`)
- `QUEUE_MAX` – maximum pending messages per connection before dropping the client (default `100`)

Tenants may also set a future `maintenance_until` timestamp in the `tenants`
table to temporarily block their own traffic. Requests made before the
timestamp receive the same 503 response with a `Retry-After` header.
Administrators can schedule this window via `POST /api/outlet/{tenant}/maintenance/schedule`.

Outlets can also be closed permanently. `POST /api/outlet/{tenant}/close` marks the
outlet as closed and schedules a data purge 90 days later. During this period
guest endpoints are blocked. Super admins may reactivate the outlet before
purge via `POST /api/admin/tenants/{id}/restore`.

Request bodies and query parameters are scrubbed of sensitive keys such as
`pin`, `utr`, `auth`, `gstin`, and `email` before being written to logs.

Media files can be persisted using either the local filesystem or S3. Configure
storage with:

- `STORAGE_BACKEND` – `local` (default) or `s3`
- `MEDIA_DIR` – directory for local file storage
- `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` – S3
  connection details used when the backend is `s3`

To cut storage costs, apply an S3 lifecycle rule that transitions objects to
infrequent access after 30 days and purges delete markers after a week:

```json
{
  "Rules": [
    {
      "ID": "media-ia",
      "Filter": {"Prefix": ""},
      "Status": "Enabled",
      "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}],
      "Expiration": {"Days": 7, "ExpiredObjectDeleteMarker": true}
    }
  ]
}
```

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

At startup the API validates that critical variables like `DB_URL` and
`REDIS_URL` are present. CI runs `scripts/env_audit.py` during linting to
keep `.env.example` in sync, and you can run the script locally to compare
`.env.example` against the required list and spot missing keys.

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

## Database performance

Migration `0010_hot_path_indexes` adds indexes on frequently queried columns
and, when running on PostgreSQL, ensures monthly partitions for `invoices` and
`payments` based on `created_at`. SQLite deployments skip the partition step but
still benefit from the new indexes.

## Continuous Integration

GitHub Actions runs the test suite along with `pre-commit`, `pa11y-ci`, `pip-audit`, and `gitleaks` for
all pull requests. To mirror these checks locally:

```bash
pip install pre-commit pip-audit gitleaks
pre-commit run --all-files
npx pa11y-ci -c pa11y-ci.json
pip-audit
gitleaks detect -c .gitleaks.toml
```

## Localization

Translation files live in `api/app/i18n`. Verify that English, Hindi and Gujarati
JSON files share the same keys:

```bash
python scripts/i18n_lint.py
```

The CI workflow runs this lint to prevent missing translations.

## End-to-End Tests

Playwright-based smoke tests cover a guest's ordering flow. Run them headlessly:

```bash
cd e2e/playwright
npm install
npm test
```

## API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://localhost:8000/health> for liveness and <http://localhost:8000/ready> for readiness checks.
Use `/support/contact` to fetch support email, phone, hours, documentation links, and legal policy URLs.
Legal policy pages are available at `/legal/{page}` (for example, `/legal/privacy` or `/legal/terms`) and support optional outlet branding.
Bundled diagnostics for an outlet can be downloaded by admin users at `/api/outlet/{tenant}/support/bundle.zip`.
Browsers requesting `text/html` receive simple static pages for 403, 404, and 500 errors.


All API responses use a standard envelope:

- Success: `{ "ok": true, "data": ... }`
- Error: `{ "ok": false, "error": { "code": ..., "message": ... } }`

### Onboarding Wizard

A minimal onboarding flow captures tenant details:

- `POST /api/onboarding/start` – create a session and return `onboarding_id`.
- `POST /api/onboarding/{id}/profile` – set name, address, logo, timezone and language.
- `POST /api/onboarding/{id}/tax` – store GST mode and registration info.
- `POST /api/onboarding/{id}/tables` – allocate tables and assign QR tokens.
- `POST /api/onboarding/{id}/payments` – configure payment modes and VPA.
- `POST /api/onboarding/{id}/finish` – finalize and activate the tenant.

### QR Pack

- `GET /api/outlet/{tenant}/qrpack.pdf?size=A4&per_page=12&show_logo=true&label_fmt=Table%20{n}` – generate a printable sheet of table labels with QR codes and the outlet logo.
  - `size` may be `A4`, `A3` or `Letter`
  - `per_page` accepts `6`, `12` or `24` (max `24`)
  - `show_logo` toggles the outlet logo on each page
  - `label_fmt` customises table labels; `{n}` is replaced with the table number and `{label}` with the base label
  - responses are cached in Redis for ten minutes and the endpoint is rate-limited to one request per minute per tenant
- `POST /api/outlet/{tenant}/tables/{code}/qr/rotate` – rotate a table's QR token, returning a new deeplink and QR image.

### Coupons

Coupons can be marked as stackable and may specify a per-invoice `max_discount` cap. When multiple stackable coupons are applied, the invoice `bill_json` records the `applied_coupons` and the combined `effective_discount`.

Attempts to combine a non-stackable coupon with others raise a `CouponError` with code `NON_STACKABLE`.

### Feedback

- `POST /api/outlet/{tenant}/feedback` – submit a thumbs-up or thumbs-down rating with optional note using a guest token.
- `GET /api/outlet/{tenant}/feedback/summary?range=30` – aggregate ratings for admins over the last `range` days (default 30).

### Super Admin

The backend exposes a super-admin endpoint used for tenant provisioning:

- `POST /api/super/outlet` – create an outlet and run tenant migrations. The
  router is present but not yet included in the main application.

### Guest Menu

A guest-facing router exposes menu data for a specific table:

- `GET /g/{table_token}/menu` – list menu categories and items. Responses
  include an `ETag` derived from a menu version that increments whenever the
  menu is modified, ensuring caches invalidate reliably.
- `GET /h/{room_token}/menu` – list menu for hotel rooms.
- `POST /h/{room_token}/order` – place a room service order.
- `POST /h/{room_token}/request/cleaning` – request housekeeping for the room.
- `POST /g/{table_token}/bill` – generate a bill; payload may include an optional `tip` and `coupons` list.


This router relies on tenant-specific databases and is not wired into the
application yet.
Guest endpoints honor the `Accept-Language` header and return localized UI labels
for menu actions such as **Order**, **Pay**, and **Get Bill**. English is the
default with Hindi and Gujarati stubs included.

### Admin Menu

An admin-only route allows toggling item availability:

- `POST /api/outlet/{tenant_id}/menu/item/{item_id}/out_of_stock` – set an
  item's stock flag. Body: `{"flag": true|false}`. Requires an admin role.

### Dashboard

An owner-facing endpoint exposes key performance indicators for the current day:

- `GET /api/outlet/{tenant_id}/dashboard/tiles?force=true` – returns today's order count, sales total, average ETA seconds, and top items. Metrics are computed in the outlet's timezone and cached for 30s (use `force=true` to bypass cache).
- `GET /api/outlet/{tenant_id}/dashboard/charts?range=7&force=true` – returns daily sales, orders, average ticket, 7/30-day sales moving averages, hourly sales heatmap, payment mix, and anomaly flags for the last 7/30/90 days. Metrics are computed in the outlet's timezone and cached for 5 minutes (use `force=true` to bypass cache).

### Staff Login

Outlet staff can authenticate with a numeric PIN to perform protected actions:

- `POST /api/outlet/{tenant}/staff/login` – verify a PIN and receive a short-lived JWT.
- `GET /api/outlet/{tenant}/staff/me` – example protected route requiring the JWT.

### Magic Link Login

Owners can authenticate using a passwordless email flow:

- `POST /auth/magic/start` – request a single-use login link. Throttled to 2/min per IP and 5/hour per email. When rate limited, clients may include an `X-Captcha-Token` HMAC generated with `CAPTCHA_SECRET` to bypass.
- `GET /auth/magic/consume?token=...` – exchange the link for a session JWT.

### Media Uploads

Admins can attach photos to items:

- `POST /api/outlet/{tenant}/media/upload` – accepts PNG, JPEG, or WebP up to
  2 MB and 4096×4096 pixels, strips EXIF metadata, re-encodes the image, and
  stores it via the configured backend. Returns `{url, key}`. Requires an admin
  role.

### Backups

Trigger a JSON backup of a tenant's database:

- `POST /api/outlet/{tenant_id}/backup` – runs the backup script and returns the
  path to the generated file.

### Daily Exports

Download a ZIP bundle of invoices, payments and per-day totals over a date range:

- `GET /api/outlet/{tenant}/exports/daily?start=YYYY-MM-DD&end=YYYY-MM-DD&limit=10000&cursor=0`
  – returns `invoices.csv`, `payments.csv` and `z-report.csv` plus individual invoice
  PDFs (or HTML when the PDF engine is unavailable). The range is capped at 31 days
  and each CSV includes at most `limit` rows (default 10k). When more rows are available
  the response includes an `X-Cursor` header that can be supplied as the `cursor`
  query parameter to resume the export.

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
- `GET /api/outlet/{tenant_id}/outbox?status=pending|delivered|failed&limit=100` – inspect notification outbox.
- `POST /api/outlet/{tenant_id}/outbox/{id}/retry` – reset a notification for another delivery attempt.
- `POST /api/outlet/{tenant_id}/webhooks/test` – send a sample webhook payload to a URL.
- `POST /api/outlet/{tenant_id}/webhooks/{id}/replay` – re-enqueue a webhook from outbox history.
- `GET /api/outlet/{tenant_id}/dlq?limit=100` – view dead-lettered notifications.
- `POST /api/outlet/{tenant_id}/dlq/{id}/requeue` – move a dead-lettered event back to the outbox.
- `DELETE /api/outlet/{tenant_id}/dlq/{id}` – discard a dead-lettered event.

Webhook payloads returned via these endpoints are scrubbed of secret fields for safe display.

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
`console`, `webhook`, `whatsapp_stub`, `sms_stub` and `email_stub` channels. The
`*_stub` channels simply log the payload and are placeholders for future
provider adapters. Each outbox row tracks delivery `attempts` and schedules
retries via `next_attempt_at`. Failed deliveries are retried with backoff
delays of 1, 5 and 30 minutes. The retry count is capped by the
`OUTBOX_MAX_ATTEMPTS` environment variable (default: 5). Events that exceed
this limit are moved to a `notifications_dlq` table for inspection, which
records the original event and error.

### KDS SLA Watcher

`scripts/kds_sla_watch.py` scans a tenant's queue and enqueues
`kds.sla_breach` events when an item remains `in_progress` longer than the
`kds_sla_secs` setting. When breaches occur an additional
`kds.sla_breach.owner` event summarises the most delayed items and tables for
delivery via owner alert channels (WhatsApp, email or Slack). Schedule it
periodically:

An internal endpoint `/api/outlet/{tenant}/kds/sla/breach` lets the KDS push
breach summaries with a time window and delayed items. Owner notifications are
queued across email, WhatsApp or Slack based on alert rules.

```bash
POSTGRES_URL=sqlite:///dev_master.db \
POSTGRES_TENANT_DSN_TEMPLATE=sqlite+aiosqlite:///tenant_{tenant_id}.db \
python scripts/kds_sla_watch.py --tenant demo
```

### Real-time Updates

Connect to `ws://localhost:8000/tables/{id}/ws` to receive live order
notifications. Messages are fanned out via Redis channels named
`rt:update:{table_code}` and include the `order_id`, current `status` and
an `eta_secs` field. The ETA is computed from an exponential moving
average and decreases with elapsed prep time. It never goes below zero and
hits exactly `0` when an order is `ready` or `served`.
The API includes a Redis-backed rate limiter that blocks an IP after three consecutive failed requests.

### Guest request limits

Anonymous guest POSTs under `/g/*` are capped at 256KB. When rate limits are
exceeded, responses use error code `RATELIMITED` and include a `retry_after`
hint in seconds.

### Idempotency

POST requests under `/g`, `/h` and `/c` honour an `Idempotency-Key`
header. Keys must be base64 or hexadecimal strings up to 128 characters.
Successful responses are cached in Redis for five minutes so that network
retries receive the original body without creating duplicate records.

### Observability

Each request is tagged with a `correlation_id` that appears in the JSON logs.
All HTTP responses follow a simple envelope structure of
`{"ok": true, "data": ...}` for success or
`{"ok": false, "error": {"code": ..., "message": ...}}` for failures.
Prometheus metrics are exposed at `/metrics`. Key metrics include:

- `http_requests_total`: total HTTP requests labelled by path/method/status
- `orders_created_total`: orders created
- `invoices_generated_total`: invoices generated
- `idempotency_hits_total` / `idempotency_conflicts_total`: idempotency key usage
- `table_locked_denied_total` / `room_locked_denied_total`: requests denied due to locks
- `http_errors_total`: HTTP errors labelled by status
- `notifications_outbox_delivered_total` / `notifications_outbox_failed_total`: notification worker results
- `ws_messages_total`: WebSocket messages delivered
- `sse_clients_gauge`: currently connected SSE clients
- `digest_sent_total`: daily KPI digests sent (via route or CLI)
- Background job status: `/api/admin/jobs/status` returns worker heartbeats,
  processed counts, recent failures, and queue depths.

The `/api/outlet/{tenant_id}/digest/run` route and the `daily_digest.py` CLI both increment `digest_sent_total`.

## Daily Digest Scheduler

`scripts/digest_scheduler.py` scans all active tenants and triggers the KPI digest once the local time passes **09:00** in each tenant's timezone. The last sent date is stored in Redis under `digest:last:{tenant}` to prevent duplicates. A systemd timer (`deploy/systemd/neo-digest.timer`) runs this script every five minutes.


## Grace/Expiry Reminders

`scripts/grace_reminder.py` scans tenant subscriptions and enqueues owner alerts when a license is set to expire in 7, 3 or 1 days, or while it remains within the grace window. A systemd timer (`deploy/systemd/neo-grace.timer`) runs this helper daily.

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
numbering for each tenant can be customised via ``inv_prefix`` and an
``inv_reset`` policy (``monthly``, ``yearly`` or ``never``). With a monthly
reset, numbers include the year and month, e.g. ``INV-ABC-202402-0001``.

### Invoice PDFs

Invoices can be rendered as PDFs via ``GET /invoice/{invoice_id}/pdf``.
Specify ``?size=80mm`` for thermal receipts or ``?size=A4`` for full pages.
If WeasyPrint is unavailable, the endpoint falls back to returning the
rendered HTML.

### KOT PDFs

Kitchen Order Tickets for table, room or counter orders can be printed through
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
python scripts/tenant_qr_tools.py list_tables --tenant TENANT_ID
python scripts/tenant_qr_tools.py regen_qr --tenant TENANT_ID --table TABLE_CODE
python scripts/tenant_qr_tools.py bulk_add_tables --tenant TENANT_ID --count 10
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

To anonymize stale guest PII for a tenant, use:

```bash
python scripts/anonymize_pii.py --tenant TENANT_ID --days 30
```

This helper nulls the `name`, `phone` and `email` columns in `invoices` and
`customers` beyond the retention window and records a summary in
`audit_tenant`.

To apply the configured retention policy for a tenant, run:

```bash
python scripts/retention_enforce.py --tenant TENANT_NAME
```

The command looks up retention windows in the master database and invokes the
anonymization and sweep helpers accordingly.


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

## Troubleshooting Help

Static help pages for staff are available under `/help/{page}`. Currently
`printing`, `network`, and `qr` guides are bundled and will show the outlet's
branding when a `tenant_id` is supplied.

## Release

Run `python scripts/release_tag.py` to generate a changelog entry and tag a new version. The helper queries merged pull requests since the last tag and groups entries by label. A `release` workflow is available for manual triggering via the GitHub UI.

## Deployment

A `deploy` GitHub Actions workflow builds Docker images, verifies staging with preflight, smoke, canary, and accessibility gates, then waits for manual approval before a blue/green production rollout with automatic rollback on failure. See `docs/CI_CD.md` for details.

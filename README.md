# Neo Monorepo

This repository contains three main services:

- `api/` – FastAPI application with `/health`, `/ready` and `/time/skew` endpoints, Alembic migrations, and service helpers such as EMA-based ETA utilities with per-tenant persistence.
- `pwa/` – React + Tailwind front end with a placeholder home page and installable PWA manifest.
 - `ops/` – Docker Compose for local development.
Monitoring tools such as UptimeRobot should poll the `/status.json` endpoint for platform health. Status is persisted in Redis with `status.json` on disk as a fallback. Administrators can override it via `POST /admin/status` or the helper script in `ops/scripts/status_page.py` during incidents.
Invoices support optional FSSAI license details when provided.
QR pack generation events are audited and can be exported via admin APIs. See
[`docs/qrpack_audit.md`](docs/qrpack_audit.md) for details. For manual rollouts, `make stage` deploys to staging, `make pilot` runs the staging smoke suite, and `make prod` promotes to production.
Per-tenant product analytics can be enabled with tenant consent. See
[`docs/analytics.md`](docs/analytics.md) for setup instructions.

CSV accounting exports for sales registers and GST summaries are documented in
[`docs/accounting_exports.md`](docs/accounting_exports.md).

## Security

Owner and admin accounts can enable optional TOTP-based two-factor authentication. See [`docs/auth_2fa.md`](docs/auth_2fa.md) for available endpoints. Sensitive operations like secret rotation, full exports and tenant closure require a fresh step-up verification.

Responses include a strict Content-Security-Policy with per-request nonces applied to inline styles and scripts in printable invoices and KOT pages. HTML pages also emit a `Content-Security-Policy-Report-Only` header directing violation details to `/csp/report`. The endpoint retains the latest 500 reports for 24 hours with tokens and query strings stripped; administrators can review paginated results at `/admin/csp/reports`.

Guest-facing order endpoints accept an `Idempotency-Key` header (UUID). Successful responses are cached for 24 hours and the key is recorded in audit logs to guard against duplicate charges.

Dedicated GitHub Actions workflows run Bandit, pip-audit, and ruff on every pull request to block risky code and dependencies.

## Configuration

Runtime settings are defined in `config.json` and may be overridden by environment variables loaded from a local `.env` file. The `config.py` module exposes a `get_settings()` helper that reads both sources.

Tenants can define `happy_hour_windows` with percent or flat discounts applied during specified days and times. Enable the `FLAG_HAPPY_HOUR` feature to activate this discounting.

The configuration includes the `kds_sla_secs` threshold (default 900 seconds)
that determines how long a KDS item may remain `in_progress` before a breach
notification is triggered.

## Testing

Playwright end-to-end tests reside under `e2e/playwright`. The `kds_expo.spec.ts` test places an order, marks it ready, verifies the ticket's age increments on the `/kds/expo` dashboard, and uses the `P` hotkey to pick the ticket, asserting an `expo.picked` audit log entry. Playwright captures video and screenshots for failing tests.

The Expo dashboard also supports keyboard shortcuts; pressing `P` removes the last order from the list.

Logging can be tuned via:

- `LOG_LEVEL` – set log verbosity (default `INFO`)
- `LOG_FORMAT` – log output format (`json` or `text`, default `json`)
- `LOG_SAMPLE_2XX` – sampling rate for 2xx logs (default `0.1`)
- `LOG_SAMPLE_GUEST_4XX` – sampling rate for guest 4xx logs (default `0.1`)
- `ERROR_DSN` – optional Sentry-compatible DSN for centralized error reporting
- `MAINTENANCE` – when `1`, only admin routes are served; others return `503 {"code":"MAINTENANCE"}`
- `ENABLE_GATEWAY` – enable Razorpay/Stripe checkout routes (defaults to manual UTR when off)
- `READ_REPLICA_URL` – optional PostgreSQL DSN for read-only queries. When
  reachable, menu fetch, dashboard charts and export endpoints use this
  replica. Health is checked on startup and every 30 s; if the replica
  becomes unreachable the app falls back to the primary. The current state is
  exposed via `app.state.replica_healthy` and Prometheus gauge
  `db_replica_healthy` (1 healthy, 0 unhealthy).

Each request carries an `X-Request-ID` header. The middleware generates one
when missing, attaches it to responses, and emits a structured log line like:

```json
{"ts":"2024-01-01T00:00:00Z","level":"INFO","req_id":"abc","tenant":null,
 "user":null,"route":"/health","status":200,"latency_ms":12}
```

Forward `$request_id` from an Nginx or other reverse proxy so its access logs
share the same identifier:

```nginx
proxy_set_header X-Request-ID $request_id;
```


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
`pin`, `utr`, `auth`, `gstin`, and `email` before being written to logs. The
JSON logger further redacts phone numbers, email addresses, and UTR values in
log messages using regex filters.

## A/B testing

The API includes a deterministic allocator that maps device IDs into weighted
experiment variants. Clients can query their assignment via
`GET /api/ab/{experiment}` by providing a `device-id` header or `device_id`
query parameter. Set `FLAG_AB_TESTS=0` to globally disable experiments and
force the `"control"` variant.

Prometheus metrics capture experiment outcomes:

* `ab_exposures_total` – incremented when a variant is served.
* `ab_conversions_total` – helper counter for recording conversions. A bill
  generation records a conversion for the requester's variant.

Example:

```bash
curl -H 'device-id: 123' http://localhost:8000/api/ab/sample
{"variant": "control"}
```

To review experiment performance, aggregate stats via:

```bash
curl \
  'http://localhost:8000/exp/ab/report?experiment=sample&from=2023-01-01&to=2023-01-31'
```

```json
{
  "variant_stats": [
    {
      "name": "control",
      "exposures": 100,
      "conversions": 10,
      "conv_rate": 0.1,
      "lift_vs_control": 0.0
    }
  ]
}
```

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

## BI parquet dumps

Nightly exports for business intelligence can be generated via `scripts/bi_dump.py`. The script writes Parquet files for orders, order items and payments partitioned by date and uploads them to an S3-compatible bucket. See [`docs/bi_dumps.md`](docs/bi_dumps.md) for configuration details.

## Licensing limits

Tenants can be assigned quotas via the `license_limits` JSON column in the
`tenants` table. Supported keys include:

- `max_tables`
- `max_menu_items`
 - `max_images_mb`
- `max_daily_exports`

Exceeding any quota results in a `403 FEATURE_LIMIT` response with a helpful
hint. Administrators may inspect current usage and limits via
`GET /api/outlet/{tenant}/limits/usage` when providing an `X-Tenant-ID` header.
 The admin dashboard displays these limits with usage bars and a "Request more"
 link for contacting support via email.

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

Hot query plans are checked in CI using `scripts/plan_guard.py`, which runs
`EXPLAIN ANALYZE` and compares the p95 execution time against baselines in
`.ci/baselines/`.

## Continuous Integration

GitHub Actions runs the test suite along with `pre-commit`, `pa11y-ci`, `pip-audit`, `gitleaks`, and `trivy` for
all pull requests. To mirror these checks locally:

```bash
pip install pre-commit pip-audit
brew install gitleaks trivy # binaries: https://github.com/gitleaks/gitleaks/releases and https://aquasecurity.github.io/trivy
pre-commit run --all-files
npx pa11y-ci -c pa11y-ci.json
pip-audit
gitleaks detect -c .gitleaks.toml
docker build -t api -f Dockerfile.api .
docker build -t worker -f Dockerfile.worker .
trivy image --severity HIGH,CRITICAL api worker
```

## Accessibility

Buttons across major flows include descriptive ARIA labels, visible focus
outlines, and high-contrast color tokens. Run `npx pa11y-ci -c pa11y-ci.json`
to verify key screens remain accessible.

## Localization

Translation files live in `api/app/i18n`. A pre-commit hook verifies that English,
Hindi and Gujarati JSON files share the same keys:

```bash
pre-commit run --hook-stage manual i18n-lint --all-files
# or run directly:
python scripts/i18n_lint.py
```

The CI workflow also runs this lint to prevent missing translations.

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
Legal policy pages are available at `/legal/{page}` (for example, `/legal/privacy`, `/legal/terms`, `/legal/subprocessors`, or `/legal/sla`) and support optional outlet branding.
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
- Tenants may also define rounding policies:
  - `gst_rounding` – either `item-wise` or `invoice-total`
  - `rounding_mode` – one of `half-up`, `bankers`, `ceil` or `floor`
  - `rounding` – `nearest_1` or `none` for ₹0.01 totals
- Invoices list per-item GST% and HSN codes with CGST/SGST or IGST tax lines; composition mode omits tax lines.
- `POST /api/onboarding/{id}/tables` – allocate tables and assign QR tokens.
- `POST /api/onboarding/{id}/payments` – configure payment modes and VPA.
- `POST /api/onboarding/{id}/finish` – finalize and activate the tenant.

Admins can also use the `/admin/onboarding` web wizard for a guided setup. The
wizard saves progress locally so owners can return and complete steps later.

### QR Pack

- `GET /api/outlet/{tenant}/qrpack.pdf?size=A4&per_page=12&show_logo=true&label_fmt=Table%20{n}` – generate a printable sheet of table labels with QR codes and the outlet logo.
  - `size` may be `A4`, `A3` or `Letter`
  - `per_page` accepts `6`, `12` or `24` (max `24`)
  - `show_logo` toggles the outlet logo on each page
  - `label_fmt` customises table labels; `{n}` is replaced with the table number and `{label}` with the base label
  - responses are cached in Redis for ten minutes and the endpoint is rate-limited to one request per minute per tenant
- `GET /api/admin/outlets/{tenant}/qrposters.zip?size=A4` – download a ZIP of A4 or A5 QR posters for each table.
- `POST /api/outlet/{tenant}/tables/{code}/qr/rotate` – rotate a table's QR token, returning a new deeplink and QR image.

### Coupons

Coupons can be marked as stackable and may specify a per-invoice `max_discount` cap. When multiple stackable coupons are applied, the invoice `bill_json` records the `applied_coupons` and the combined `effective_discount`.

Attempts to combine a non-stackable coupon with others raise a `CouponError` with code `NON_STACKABLE`.

Coupons may also define per-day, per-guest and per-outlet usage caps along with `valid_from`/`valid_to` windows. Usage is audited and exceeding a cap results in a `CouponError` with a `hint` describing the limitation.

### Feedback

- `POST /api/outlet/{tenant}/feedback` – submit a thumbs-up or thumbs-down rating with optional note using a guest token.
- `GET /api/outlet/{tenant}/feedback/summary?range=30` – aggregate ratings for admins over the last `range` days (default 30).
- `POST /api/pilot/{tenant}/feedback` – submit an NPS score (0-10) with optional comment.
\

### Super Admin

The backend exposes a super-admin endpoint used for tenant provisioning:

- `POST /api/super/outlet` – create an outlet and run tenant migrations. The
  router is present but not yet included in the main application.

### Guest Menu

A guest-facing router exposes menu data for a specific table:

- `GET /g/{table_token}/menu` – list menu categories and items. Responses
  include an `ETag` derived from a menu version that increments whenever the
  menu is modified, ensuring caches invalidate reliably. Use
  `filter=dietary:vegan,-allergen:nuts` to include only items matching dietary
  tags and excluding specific allergens. Menu items may expose server-priced
  modifiers or optional combos with pricing calculated on the server when
  orders are placed.
- `GET /h/{room_token}/menu` – list menu for hotel rooms.
- `POST /h/{room_token}/order` – place a room service order.
- `POST /h/{room_token}/request/cleaning` – request housekeeping for the room.
- `POST /g/{table_token}/bill` – generate a bill; payload may include an optional `tip` and `coupons` list.
- `GET /guest/receipts?phone=XXXXXXXXXX` – list up to the last ten redacted
  receipts for the contact (use `email=` to look up by email). Retention is 30
  days by default and may be extended per tenant.


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
- `GET /api/outlet/{tenant}/staff/shifts?date=YYYY-MM-DD` – staff shift summary with logins,
  KOT accepted, tables cleaned, voids and total login time. Use `format=csv` for CSV export.

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
- `GET /admin/integrations` – list available webhook integration types with sample payloads.
- `POST /admin/integrations/{type}/probe` – probe a webhook destination and send a sample payload.
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
retries via `next_attempt_at`. Failed deliveries use exponential backoff with
jitter (roughly 1s, 5s, 30s, 2m and 10m). A Redis-backed circuit breaker tracks
consecutive failures per destination using keys `cb:{hash}:state`,
`cb:{hash}:fails` and `cb:{hash}:until`. It opens after the threshold is
exceeded, stays open for a cooldown period and then permits a half-open probe
before returning to the closed state on success.
The retry count is capped by the `OUTBOX_MAX_ATTEMPTS` environment variable
(default: 5). Events that exceed this limit are moved to a `notifications_dlq`
table for inspection, which records the original event and error.

Additional environment variables:

* `CB_FAILURE_THRESHOLD` – failures before opening the breaker (default: 8)
* `CB_COOLDOWN_SEC` – seconds the breaker remains open (default: 600)
* `CB_HALFOPEN_TRIALS` – allowed requests during half-open state (default: 1)
* `CB_KEY_PREFIX` – Redis key prefix (default: `cb:`)

Metrics exposed under `/metrics` include `webhook_attempts_total`,
`webhook_failures_total` and `webhook_breaker_state`. Attempts and failures are
labelled by destination hash, while the breaker gauge uses the same hash and
reports `0` when closed, `1` when open and `2` when half-open.

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

### Guest Notifications

Guests who share a phone number and opt in to WhatsApp receive order status
updates when their order is accepted, out for delivery, or ready. Messages are
queued through the notification outbox and delivered via the configured
WhatsApp provider. Set `WHATSAPP_GUEST_UPDATES_ENABLED=true` and enable the
`WA_ENABLED` feature flag (`FLAG_WA_ENABLED=1`) to activate these messages.
The API includes a Redis-backed rate limiter that blocks an IP after three consecutive failed requests.

### Guest request limits

Anonymous guest POSTs under `/g/*` are capped at 256KB. When rate limits are
exceeded, endpoints return HTTP 429 with JSON
`{"code": "RATE_LIMIT", "hint": "retry in 10s"}`.

### Idempotency

POST requests under `/g`, `/h` and `/c` honour an `Idempotency-Key`
header. Keys must be base64 or hexadecimal strings up to 128 characters.
Successful responses are cached in Redis for five minutes so that network
retries receive the original body without creating duplicate records.

### Observability

Each request is tagged with a `correlation_id` that appears in the JSON logs.
All HTTP responses follow a simple envelope structure of
`{"ok": true, "data": ...}` for success or
`{"ok": false, "error": {"code": ..., "message": ...}}` for failures,
except rate-limit errors which return
`{"code": "RATE_LIMIT", "hint": "retry in Xs"}`.
Prometheus metrics are exposed at `/metrics`. Key metrics include:

- `http_requests_total`: total HTTP requests labelled by path/method/status
- `orders_created_total`: orders created
- `invoices_generated_total`: invoices generated
- `idempotency_hits_total` / `idempotency_conflicts_total`: idempotency key usage
- `table_locked_denied_total` / `room_locked_denied_total`: requests denied due to locks
- `http_errors_total`: HTTP errors labelled by status
- `slo_requests_total` / `slo_errors_total`: guest requests and errors by route
- `notifications_outbox_delivered_total` / `notifications_outbox_failed_total`: notification worker results
- `ws_messages_total`: WebSocket messages delivered
- `sse_clients_gauge`: currently connected SSE clients
- `digest_sent_total`: daily owner digests (orders, avg prep time, top items, comps, tips, gateway fee estimate) sent via email/WhatsApp or CLI
- `slo_requests_total` / `slo_errors_total`: per-route SLO tracking
- Background job status: `/api/admin/jobs/status` returns worker heartbeats,
  processed counts, recent failures, and queue depths.
Rolling 30-day error budgets per guest route are exposed at `/admin/ops/slo`.
- Owner SLA metrics are available from `/owner/sla` for uptime, webhook success,
  median prep time, and KOT delay alerts. Each value includes a corresponding
  `<field>_trend` delta comparing the current 7‑day window with the preceding
  one. The PWA uses these deltas to render arrows and colors based on SLA
  thresholds.
  
  Example:
  ```json
  {
    "data": {
      "uptime_7d": 100.0,
      "uptime_trend": 10.0,
      "webhook_success": 0.67,
      "webhook_success_trend": -0.08,
      "median_prep": 20.0,
      "median_prep_trend": -20.0,
      "kot_delay_alerts": 2,
      "kot_delay_alerts_trend": 1
    }
  }
  ```
  
  UI thresholds (configurable in `OwnerSlaWidget.jsx`): uptime ≥99.9% green,
  ≥99% yellow; webhook success ≥99% green, ≥95% yellow; median prep <600s green,
  <900s yellow; KOT alerts 0 green, ≤3 yellow, otherwise red.
- Dead-letter queue: `/api/admin/dlq?type=webhook|export` lists failed jobs;
  `POST /api/admin/dlq/replay` re-enqueues a job by ID supplied in the JSON body.
- Pilot telemetry for ops is available at `/api/admin/pilot/telemetry` and
  reports orders/minute, prep times, queue age, latency, error rate and breaker
  status.

Rolling 30-day error budgets per route are available from the admin endpoint
`/admin/ops/slo`.

The `/api/outlet/{tenant_id}/digest/run` route and the `daily_digest.py` CLI both increment `digest_sent_total`.

## Daily Digest Scheduler

`scripts/digest_scheduler.py` scans all active tenants and triggers the KPI digest once the local time passes **09:00** in each tenant's timezone. The last sent date is stored in Redis under `digest:last:{tenant}` to prevent duplicates. A systemd timer (`deploy/systemd/neo-digest.timer`) runs this script every five minutes.

`scripts/pilot_digest.py` collects pilot-tenant telemetry (orders, notification failures, SLA breaches, breaker opens and export errors) and sends a summary via email and Slack each day at **20:00 IST**. Tenants are configured through the `PILOT_TENANTS` environment variable.

`scripts/pilot_nps_digest.py` aggregates pilot NPS feedback per outlet and emails a daily summary.


## Grace/Expiry Reminders

`scripts/grace_reminder.py` scans tenant subscriptions and enqueues owner alerts when a license is set to expire in 7, 3 or 1 days, or while it remains within the grace window. A systemd timer (`deploy/systemd/neo-grace.timer`) runs this helper daily.

## Billing

Admins can view their current plan and renewal date at `/billing`. The page links to a UPI or gateway URL for self‑serve renewals, and successful payment webhooks automatically extend the license.
Set the `LICENSE_PAY_URL` environment variable to the payment link displayed on this page.

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
python scripts/qr_poster_pack.py --tenant TENANT_ID --size A4
```

To generate a sizable dataset for local load testing, use the large outlet seeder:

```bash
POSTGRES_TENANT_DSN_TEMPLATE=sqlite+aiosqlite:///tmp/{tenant_id}.db \
python scripts/seed_large_outlet.py --tenant TENANT_ID \
    --items 5000 --tables 300 --orders 50000
```



For local scale testing, a helper seeds large volumes of data using bulk
inserts:

```bash
python scripts/seed_large_outlet.py --tenant TENANT_ID --tables 300 --items 5000 --orders 50000 --days 60
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
pip install pre-commit pytest-cov
```
Run linters and formatters:

```bash
pre-commit run --all-files
```

Run the full test suite with coverage (fails under 80%):

```bash
pytest --cov=api --cov-report=term --cov-fail-under=80
```

Run a single module or test:

```bash
pytest api/tests/test_auth.py::test_password_login_success
```

### API contract fuzzing

Critical `orders`, `billing` and `exports` routes are fuzzed with [Schemathesis](https://schemathesis.readthedocs.io/) to catch schema regressions.
Run them locally with:

```bash
pytest tests/api_contract -q
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

Static help pages for staff are available under `/help/{page}`. Guides include
`printing`, `network`, `qr`, `owner_onboarding`, `cashier_kds_cheatsheet`, and
`troubleshooting`, each showing the outlet's branding when a `tenant_id` is
supplied.

## Release

Run `python scripts/release_tag.py` to generate a changelog entry and tag a new version. Use `make release-rc` for a release candidate or `make release-ga` for a GA tag. The helper queries merged pull requests since the last tag and groups entries by label. A `release` workflow is available for manual triggering via the GitHub UI.

## Deployment

A `deploy` GitHub Actions workflow builds Docker images, verifies staging with preflight, smoke, canary, and accessibility gates, then waits for manual approval before a blue/green production rollout with automatic rollback on failure. See `docs/CI_CD.md` for details. For manual rollouts, `make stage` deploys to staging, `make pilot` runs the staging smoke suite, and `make prod` promotes to production.

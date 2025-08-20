MVP Spec — QR-based Dine-in Ordering & Billing (SaaS)
1) Scope (MVP)

QR menu & ordering (one table → one running bill; multiple rounds allowed).

Statuses: Placed → Accepted → In-Progress → Ready → Served → Cancelled (+ optional Rejected, Hold).

Live status on guest page (while open). No web-push.

Simple UPI (deep-link intent + static QR) and Cash; Card optional.

Bill generation (GST-compliant when enabled): 80 mm print & PDF.

Basic stock control (hide “Out of stock”).

EMA-based ETA (outlet-wide, last 10/20 orders).

Roles & PIN logins: Super-Admin, Outlet Admin/Manager, Cashier, Kitchen, Cleaner.

KDS: item-level and/or whole-order accept/serve (config at onboarding).

Takeaway/Counter mode (simple).

Discounts/Service charge/Tips, Coupons.

Daily closing report + email/WhatsApp + CSV/Excel export.

Multi-tenant SaaS: one master DB + separate DB per outlet.

Subscription: per table / month; 7-day grace; block orders after expiry. Subscription payments: screenshot/manual verify (no gateway yet).

Fixed QR per table; QR poster (standard size) generator.

Hybrid/offline: local server (Linux mini-PC/RPi/Windows) + cloud; queue & sync.

Security: IP rate-limit + auto-block after 3 rejections.

Audit log (retention set at onboarding).

Languages: English default; optional locales.

Deferred (post-MVP): reservations/waitlist, multi-station routing, native apps, PSP webhooks for auto-verify, table merge/transfer UI, owner read-only app, complex modifiers, per-item EMA.

2) Roles & Access (RBAC)

Super-Admin (SaaS): onboard outlets, plans, quotas, central VPA toggle, health/usage, backups policy.

Outlet Admin/Manager: menu, taxes/GST mode, coupons, staff & PINs, floor map (optional), alerts rules, day closing, reports, invoice settings, UPI VPA config.

Cashier: open/close bills, apply discounts/tips, mark payments (cash/UTR), print/PDF, verify UPI, settle, reprint.

Kitchen (KDS): view queue, accept/bump (item or whole order), mark Ready/Served, toggle stock.

Cleaner: mark “Cleaned & Ready” to unlock table.

Guest: browse menu, add to cart, place order, view status, request bill.

3) Lifecycles
Table session

Locked (no session) → Unlocked (Cleaned & Ready) → Active (running bill) → Settlement → Locked until Cleaned

Order

Placed → (Accepted|Rejected) → In-Progress → Ready → Served

Guest cannot edit after Placed. Admin can set item qty to 0 (soft-cancel).

Price never changes mid-session; new prices apply only from next QR session.

Payment

Modes: UPI / Cash (Card optional).

Flow: Generate bill → show UPI/cash → (auto or manual verification per outlet) → Settled → Table locks → Staff marks Cleaned → Unlock.

4) Key Flows
A) Onboarding (done by your team)

Create Outlet → choose domain/subdomain (with free SSL) → set GST mode (Unregistered/Composition/Registered) → rounding rule.

Choose payment options (UPI VPA: outlet VPA or central VPA).

Choose verification mode (Auto via webhook – later / Manual UTR).

Choose EMA window (10 or 20), languages, KDS mode (item vs whole-order).

Import menu (Excel) + upload photos; mark veg/non-veg/allergen; optional HSN/GST.

Create tables & print QR posters (std size).

Create staff PINs; configure alert rules; set audit retention; set backup policy (local + S3/MinIO).

Subscription plan (per table / month), grace 7 days.

B) Guest QR Session (PWA)

Scan fixed table QR → load menu → add items → Place Order → live status (poll via WS/SSE) → Get Bill → invoice + UPI deep-link/QR → payment → (verify) → thank you & rating.

C) KDS

New orders list → swipe Accept → items count down by EMA → In-Progress → Ready → Served. Color/time alerts; optional sound.

D) Cashier/Billing

Open running bill → apply discounts/service charge/tips/coupon → Generate Invoice (GST layout as per mode) → show payment panel → verify UPI (auto/manual) or mark Cash → Settle → triggers “Needs Cleaning”.

E) Cleaning Lock

After settlement: table is Locked → cleaner scans staff QR/PIN → Mark Cleaned & Ready → unlocks for next guest.

F) Stock Toggle

Kitchen/Admin flips item “Out of stock” → instantly hides for new adds; existing cart unaffected.

G) Expiry/Grace

If expired and past 7-day grace → block all new orders (show renewal banner). Existing settled bills still viewable.

H) Takeaway/Counter

No table; pseudo-table TA-###; otherwise identical flow.

5) Data Model
Master DB (Postgres)
tenants(id uuid pk, name, code, status, created_at)
outlets(id uuid pk, tenant_id fk, name, domain, local_fallback_host, gst_mode enum, rounding enum, currency, tz, vpa_mode enum, vpa_value, languages jsonb, ema_window int, kds_mode enum, otp_required bool default false, features jsonb, created_at)
subscriptions(id pk, outlet_id fk, plan 'per_table', tables_licensed int, status enum, starts_on, ends_on, grace_until, last_payment_note, screenshot_url, created_at)
users(id pk, tenant_id fk, email, phone, password_hash, role enum['superadmin','owner','ops'], is_active)
outlet_staff(id pk, outlet_id fk, name, role enum['admin','cashier','kitchen','cleaner'], pin char(6), is_active)
tables(id pk, outlet_id fk, code, qr_token, is_active)
alerts_rules(id pk, outlet_id fk, event enum, channels jsonb, enabled bool)
backups_policy(id pk, outlet_id fk, dest enum['local','s3','both'], retention_days int)
audit_master(id bigserial pk, actor, action, target, details jsonb, at timestamptz)

Tenant DB (per Outlet)
settings(id pk, key text unique, value jsonb)
menu_categories(id pk, name, sort)
menu_items(id pk, category_id fk, name, price numeric(10,2), is_veg bool, allergens text[], photo_url, gst_rate numeric(4,2), hsn_sac text, show_fssai bool, is_active bool, out_of_stock bool, tags text[])
tables(id pk, code unique, qr_token, section text null, is_active bool)
orders(id uuid pk, table_id fk, status enum, placed_at, accepted_at, ready_at, served_at, cancelled_at, channel enum['dine','takeaway'], note text)
order_items(id pk, order_id fk, item_id fk, name_snapshot, price_snapshot, qty int, status enum, cancelled bool default false)
invoices(id pk, order_group_id uuid, number text unique, bill_json jsonb, gst_breakup jsonb, total numeric(12,2), mode enum['b2c','b2b'], buyer jsonb, created_at)
payments(id pk, invoice_id fk, mode enum['upi','cash','card'], amount numeric, utr text, verified bool, verified_by, created_at)
ema_stats(id pk, window int, last_n jsonb, ema_seconds numeric)
customers(id pk, phone, name, consent bool, retention_until date)
coupons(id pk, code, type enum['flat','percent'], value numeric, active bool, valid_from, valid_to, usage_limit)
audit(id bigserial pk, actor, role, action, entity, entity_id, diff jsonb, at timestamptz)
heartbeat(id pk, device text, last_seen timestamptz, status enum)

Redis (per outlet namespace)

qr:{table_code}:session → {session_id, started_at, price_lock_version}

cart:{session_id} → list of {item_id, name, price, qty}

kds:queue → order ids / item tickets

rt:update:{table_code} pub/sub for WS/SSE

ratelimit:ip:{ip} counters

blocklist:ip set

sync:outbox for offline → cloud

locks:table:{table_id} mutex for session start/settle

6) APIs (FastAPI)

Base paths: /api/super, /api/outlet/{outlet_id}, /g (guest).

Auth

POST /api/outlet/{id}/auth/login (email+password) → JWT

POST /api/outlet/{id}/auth/pin (pin) → short-lived token (role: cashier/kitchen/cleaner)

Guest

GET /g/{table_token}/menu → categories+items (filtered, stock)

POST /g/{table_token}/cart → add/update/remove

POST /g/{table_token}/order → create order (lock edit)

GET /g/{table_token}/status (WS/SSE /g/{token}/ws)

POST /g/{table_token}/bill → generate invoice draft

GET /g/{table_token}/pay/upi → deep-link params + static QR

GET /g/{table_token}/invoice/{number}.pdf

KDS / Kitchen

GET /api/outlet/{id}/kds/queue

POST /api/outlet/{id}/kds/order/{order_id}/accept

POST /api/outlet/{id}/kds/item/{item_id}/progress|ready|served

POST /api/outlet/{id}/stock/{item_id}/toggle

Cashier / Admin

GET /api/outlet/{id}/tables (status list or floor map)

POST /api/outlet/{id}/bill/{session_id}/generate

POST /api/outlet/{id}/payment/{invoice_id}/mark (mode, amount, utr?, verified?)

POST /api/outlet/{id}/settle/{session_id}

POST /api/outlet/{id}/clean/{table_id}/mark-ready

POST /api/outlet/{id}/coupon/apply

POST /api/outlet/{id}/menu/import (Excel)

POST /api/outlet/{id}/qr/{table_id}/poster (PDF)

Reports: GET /api/outlet/{id}/reports/sales?from&to, .../top-items, .../z-report

Super-Admin

POST /api/super/outlet (create + DNS/SSL)

POST /api/super/subscription/{outlet_id}/update

POST /api/super/payment-proof/{outlet_id} (subscription screenshot)

GET /api/super/health, GET /api/super/usage

Realtime

WS channels:

/ws/outlet/{id}/kds

/ws/outlet/{id}/cashier

/g/{token}/ws

7) EMA Prep-time

Keep a rolling array of last N served orders’ actual prep seconds → ema = α*t + (1-α)*ema_prev with α = 2/(N+1).

Store ema_seconds in ema_stats; expose to KDS & guest eta.

8) Reporting (MVP)

Daily/weekly revenue, payment mix, GST breakup (if applicable), table-wise orders, top items, voids/cancellations, average prep time.

Z-report: totals, tax, discounts, service charge, tips, cash vs UPI, opening/closing remarks.

9) Alerts (Rule-based)

Events: new_order, bill_ready, payment_received, day_close, device_offline, subscription_expiring.
Channels: Email (default), WhatsApp/SMS (optional). Config per outlet.

10) Security

IP rate limit: sliding window; after 3 order rejections, add IP to blocklist for X hours (config).

QR token is opaque; server enforces one active session per table.

Staff PINs rotate; PIN attempts limit + cooldown.

All writes audited (who/when/what).

11) Offline/Hybrid Architecture

Local node (Docker): API + Redis + Postgres(outlet) + file cache; LAN DNS alias (e.g., kds.local).

Cloud: master API + master Postgres + object storage (MinIO/S3) + central Redis for coordination.

Sync: append-only outbox + idempotent upserts; order IDs are UUID; invoice numbers generated only when online or by local allocator with gap-free per-outlet sequence & conflict guard.

12) Deployment (Self-host, Linux)

Containers: api, worker, scheduler, postgres-master, postgres-tenant, redis, minio, caddy|traefik, nginx.
TLS: Caddy (Let’s Encrypt) for wildcard/subdomains; free SSL by default.
Backups: nightly pg_dump (tenant + master) to local disk and S3/MinIO; retention per policy.
Monitoring: heartbeats + basic Prometheus exporters; alert rules to email/WhatsApp.
Env (examples):

JWT_SECRET=...
DB_MASTER_URL=...
REDIS_URL=...
S3_ENDPOINT=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
DEFAULT_TZ=Asia/Kolkata

13) UI (PWA) — Pages & Widgets
Guest

Menu (search, veg filter, photos, tags/FSSAI icons), Cart, Order Status (live), Get Bill, UPI pay, Rating.

Staff (responsive)

KDS: columns by status, swipe-to-bump, color timers, sounds.

Tables: grid + optional simple floor map; status chips (Active/Locked/Needs Cleaning).

Billing: running bill view → discounts/tips/coupons → invoice → payment verify → settle → print/PDF.

Menu & Stock: quick toggle Out of Stock.

Reports: today snapshot; Z-report button.

Settings: GST mode, VPA, rounding, languages, alerts, PINs.

Super-Admin

Onboarding wizard, Domains/SSL, Subscription, Health, Backups.

14) Excel Menu Template (import)

Columns:
category, item_name, price, is_veg(Y/N), allergens(csv), gst_rate(%), hsn_sac, show_fssai(Y/N), is_active(Y/N), tags(csv), photo_filename
(Photos uploaded separately; match by filename.)

15) Documents & Prints

Invoice 80 mm: logo, outlet details, GSTIN (if any), HSN/SAC lines (if applicable), CGST/SGST split, rounding line, total, mode, UTR (if UPI), QR receipt mini-code (optional), thank-you + rating link.

QR Poster: table code, scan hint, outlet logo; A5 & 3×3-inch standard.

16) Test Scenarios (must pass)

New outlet onboarding → menu import → QR poster gen → first order end-to-end.

Multi-round ordering → single consolidated invoice.

KDS accept/ready/served updates reflect on guest page instantly.

UPI deep-link opens major PSPs; static QR scan works; manual UTR verify flow.

Cash settlement with split payments (UPI + Cash).

GST registered vs unregistered invoices.

Expiry & 7-day grace → block on day 8.

IP rejected ×3 → blocked; unblocks after window.

Offline local orders queue → sync on reconnect; invoice numbering preserved.

After settlement, table locked until cleaner marks ready.

17) Minimal DB DDL (examples)
-- master: outlets
create table outlets(
  id uuid primary key, tenant_id uuid not null,
  name text, domain text, gst_mode text, rounding text,
  currency text default 'INR', tz text default 'Asia/Kolkata',
  vpa_mode text, vpa_value text, languages jsonb default '["en"]'::jsonb,
  ema_window int default 10, kds_mode text default 'order',
  created_at timestamptz default now()
);

-- tenant: orders
create type order_status as enum('placed','accepted','in_progress','ready','served','cancelled','rejected','hold');

create table orders(
  id uuid primary key,
  table_id uuid not null,
  status order_status not null default 'placed',
  channel text default 'dine',
  placed_at timestamptz default now(),
  accepted_at timestamptz, ready_at timestamptz, served_at timestamptz, cancelled_at timestamptz
);

18) Event Bus (internal)

Emit: order.placed, order.accepted, order.ready, order.served, bill.generated, payment.verified, table.settled, table.locked, table.cleaned, device.offline, subscription.expiring.
Consumers: alerts sender, EMA updater, report aggregator, sync worker.

19) Security & Compliance Notes

Hash passwords (Argon2); store PINs salted/hashed.

CSRF for non-API forms; CORS locked to domains.

Logging PII minimal; customer retention per outlet policy.

GDPR-style purge function for customer contacts (if configured).

20) “Day-1” Deliverables (you can start immediately)

Monorepo scaffold (FastAPI + Postgres + Redis + Caddy + MinIO via Docker Compose).

Base schemas (master + tenant) and migrator.

Auth (email/password + PIN), RBAC.

Guest menu/cart/order endpoints + WS/SSE.

KDS endpoints + simple web UI.

Billing engine (GST modes, rounding) + 80 mm print/PDF.

UPI deep-link & static QR generator.

QR poster generator (A5 + 3×3-inch).

Basic reports + Z-report export.

Subscription guard (per table/month, grace 7 days).

Offline outbox + sync skeleton.

Alert rules (email) + heartbeat.

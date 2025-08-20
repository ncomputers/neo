# Software Requirements Specification (SRS)
**Version:** 1.0

## 1. Functional Requirements (FR)
FR1: Guest reads fixed table QR and loads menu (with veg filter, photos, FSSAI icons).  
FR2: Guest adds items to cart; places order (no edits after placed).  
FR3: KDS receives orders instantly; can Accept/Progress/Ready/Serve by item or whole order.  
FR4: Admin/Cashier generates invoice (GST modes), applies discounts/tips/coupons.  
FR5: Payment modes UPI/Cash; split payments supported; UTR/manual verify (auto webhook later).  
FR6: After settlement, table locks; cleaner must mark "Cleaned & Ready".  
FR7: Stock toggle hides items for new adds.  
FR8: Daily closing report (Z-report) with email & CSV/Excel.  
FR9: Subscription per table/month with 7-day grace; block new orders after expiry.  
FR10: Alerts: new_order, bill_ready, payment_received, day_close, offline, subscription_expiring.  

## 2. Non‑Functional Requirements (NFR)
- **Performance:** API p95 < 300 ms (LAN), < 700 ms (cloud). KDS render < 100 ms per update.
- **Reliability:** Local node stores to durable queue; resume sync on reconnect.
- **Security:** Argon2 password hashing; rate limit; IP block after 3 rejections; JWT auth.
- **Scalability:** Per‑outlet DB; connection pools; Redis for realtime/pubsub and caches.
- **Maintainability:** Typed FastAPI; Alembic migrations; CI with tests.
- **Portability:** Dockerized; single‑host compose for self‑host; cloud optional.
- **Observability:** Structured logs; minimal metrics; audit trails.

## 3. Data
- **Master DB:** tenants/outlets/subscriptions/staff/alerts/backups/audit_master.
- **Tenant DB:** menu/tables/orders/order_items/invoices/payments/customers/coupons/audit/ema_stats.
- **Redis:** sessions, carts, kds queue, pub/sub topics, rate‑limits, outbox.

## 4. External Interfaces
- UPI deep‑link intents; static QR content generator.
- Email (SMTP); WhatsApp/SMS (future).

## 5. Constraints & Assumptions
- Single active session per table.  
- Price snapshots stored per item at order time.  
- Invoice numbers per outlet, reset policy configurable.

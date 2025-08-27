# Core Indexing

This project uses a set of targeted indexes to keep hot multi-tenant queries fast without over-indexing. Each index below lists the query pattern it accelerates.

## Orders
- `idx_orders_tenant_status_created` – fetch KDS/status windows by tenant and status ordered by creation time.
- `idx_orders_tenant_table_open` – find open orders for a table.
- `ux_orders_tenant_idempotency` – enforce idempotency per tenant.
- `brin_orders_created` – speed large date range exports.

## Order Items
- `idx_order_items_order` – join items to an order.
- `idx_order_items_tenant_menuitem` – tenant scoped menu item analytics excluding soft deletes.

## Payments
- `idx_payments_tenant_order_status` – settlement lookups per order.
- `ux_payments_tenant_utr` – unique UTR per tenant.

## Menu Items
- `idx_menu_tenant_category_active` – list active menu items in a category.
- `gin_menu_dietary`, `gin_menu_allergens`, `gin_menu_tags` – filter JSONB attributes with `?`/`?|`.
- `gin_menu_search` – full-text search.

## Tables
- `ux_tables_tenant_code_live` – tenant unique table codes.
- `idx_tables_tenant_state_updated` – poll table state changes.

## Misc
- `idx_webhooks_tenant_due` – schedule pending webhook retries.
- `idx_exports_tenant_created` – list export jobs by date.
- `brin_audit_created` – append-only audit log range scans.
- `ux_devices_tenant_fingerprint` – deduplicate devices.
- `idx_promos_tenant_code_active` – resolve active promo codes.
- `idx_ratelimit_tenant_ip_window` – rate limit lookups.

Partial indexes skip soft-deleted or closed records, keeping btrees small. BRIN is used for very large, append-only tables (`orders`, `audit_log`) where a tiny index can satisfy range scans. GIN accelerates JSONB and full-text searches. Covering indexes (`INCLUDE`) make common `orders` selects index-only.

## Verification
1. Load sample data via `scripts/seed_large_outlet.py`.
2. Run `pytest api/tests/test_indexes_explain.py` and confirm the plans show `Index Scan` or `Bitmap Index Scan` on the expected index.
3. Monitor `plan_guard.py` so P95 for hot queries improves or stays within 20% of baseline.

Autovacuum should keep indexes healthy. Run `REINDEX CONCURRENTLY` only if bloat is observed and schedule `ANALYZE` after large imports.

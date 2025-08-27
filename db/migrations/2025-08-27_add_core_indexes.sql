-- ORDERS: KDS / open tabs / time filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_tenant_status_created
  ON orders (tenant_id, status, created_at DESC)
  INCLUDE (total_amount, table_id)
  WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_tenant_table_open
  ON orders (tenant_id, table_id, created_at DESC)
  WHERE closed_at IS NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_orders_tenant_idempotency
  ON orders (tenant_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- For large date-range exports; BRIN is tiny and fast for append-only
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_orders_created
  ON orders USING BRIN (created_at) WITH (pages_per_range=64);

-- ORDER_ITEMS: joins + analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_order
  ON order_items (order_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_tenant_menuitem
  ON order_items (tenant_id, menu_item_id)
  WHERE deleted_at IS NULL;

-- PAYMENTS: settlement & UTR lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_tenant_order_status
  ON payments (tenant_id, order_id, status)
  WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_payments_tenant_utr
  ON payments (tenant_id, utr)
  WHERE utr IS NOT NULL;

-- MENU: category listing, active menus, search, filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_tenant_category_active
  ON menu_items (tenant_id, category_id, sort_order)
  WHERE is_active = TRUE AND deleted_at IS NULL;

-- JSONB filters for dietary/allergens/tags (use ?/?| operators)
CREATE INDEX CONCURRENTLY IF NOT EXISTS gin_menu_dietary
  ON menu_items USING GIN ((coalesce(dietary, '[]'::jsonb)));

CREATE INDEX CONCURRENTLY IF NOT EXISTS gin_menu_allergens
  ON menu_items USING GIN ((coalesce(allergens, '[]'::jsonb)));

CREATE INDEX CONCURRENTLY IF NOT EXISTS gin_menu_tags
  ON menu_items USING GIN ((coalesce(tags, '[]'::jsonb)));

-- Full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS gin_menu_search
  ON menu_items USING GIN (search_tsv);

-- TABLES: fast occupancy/state lookups
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_tables_tenant_code_live
  ON tables (tenant_id, table_code)
  WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tables_tenant_state_updated
  ON tables (tenant_id, state, updated_at DESC);

-- WEBHOOK queue: next attempt scheduler
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_tenant_due
  ON webhook_events (tenant_id, next_attempt_at)
  WHERE state = 'pending';

-- EXPORT jobs listing by date
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exports_tenant_created
  ON exports (tenant_id, created_at DESC);

-- AUDIT: huge, append-only; BRIN wins
CREATE INDEX CONCURRENTLY IF NOT EXISTS brin_audit_created
  ON audit_log USING BRIN (created_at);

-- DEVICES: fingerprint uniqueness per-tenant
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_devices_tenant_fingerprint
  ON devices (tenant_id, fingerprint)
  WHERE deleted_at IS NULL;

-- PROMOS: fast code resolve when active
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_promos_tenant_code_active
  ON promos (tenant_id, code)
  WHERE is_active = TRUE AND deleted_at IS NULL;

-- RATE LIMIT: ip window lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ratelimit_tenant_ip_window
  ON rate_limits (tenant_id, ip, window_start);

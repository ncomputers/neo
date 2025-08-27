# Tenant Performance Indexes

Migration `0006_perf_indexes` adds several indexes to speed up common list and queue operations:

- `orders(status, placed_at)`
- `order_items(order_id)`
- `invoices(created_at)`
- `payments(invoice_id)`
- `tables(code)`
- `tables(qr_token)`
- `room_orders(status, placed_at)` *(if the table exists)*
- `counter_orders(status, placed_at)` *(if the table exists)*

Migration `20250825_0727_hot_indexes` extends these with additional hot-path
composite indexes, created concurrently on PostgreSQL for dashboards and
exports:

- `idx_inv_tenant_created` on `invoices(tenant_id, created_at DESC)`
- `idx_pay_invoice_created` on `payments(invoice_id, created_at DESC)`
- `idx_orders_tenant_status_created` on `orders(tenant_id, status, created_at DESC)`
- `idx_audit_tenant_created` on `audit_tenant(tenant_id, created_at DESC)`

Run tenant migrations as usual to apply the indexes. Supply a DSN template via
``--dsn-template`` or the ``POSTGRES_TENANT_DSN_TEMPLATE`` environment
variable::

```bash
POSTGRES_TENANT_DSN_TEMPLATE=postgresql+asyncpg://u:p@host:5432/tenant_{tenant_id} \
python scripts/tenant_migrate.py --tenant <tenant>
```

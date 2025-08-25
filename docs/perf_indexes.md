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

Migration `0008_hot_path_indexes` extends these with additional hot-path
composite indexes optimised for tenant queries:

- `invoices(tenant_id, created_at DESC)`
- `payments(invoice_id, created_at DESC)`
- `orders(tenant_id, status, created_at DESC)`
- `audit_tenant(tenant_id, created_at DESC)`

Run tenant migrations as usual to apply the indexes:

```bash
python scripts/tenant_migrate.py --tenant <tenant>
```

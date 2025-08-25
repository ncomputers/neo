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

Migration `0010_hot_indexes_partitions` extends these with additional hot-path indexes and optional monthly partitions:

- `invoices(created_at, tenant_id)`
- `payments(invoice_id, created_at)`
- `orders(status, created_at)`
- `order_items(order_id)` *(ensures the index exists)*
- `audit_tenant(created_at)`

On PostgreSQL deployments, the migration also attempts to create a monthly
partition for the `invoices` and `payments` tables based on `created_at`.

Run tenant migrations as usual to apply the indexes:

```bash
python scripts/tenant_migrate.py --tenant <tenant>
```

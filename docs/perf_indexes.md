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

Run tenant migrations as usual to apply the indexes:

```bash
python scripts/tenant_migrate.py --tenant <tenant>
```

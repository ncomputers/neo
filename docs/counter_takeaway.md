# Counter Takeaway Flow

This flow allows a tenant to handle takeaway orders through a single QR code at each sales counter.

## Schema
- `counters` – stores counter code and QR token.
- `counter_orders` – links orders to counters and tracks their status with timestamps.
- `counter_order_items` – snapshots menu item name, price and quantity for every order line.

## Routes
- `GET /c/{counter_token}/menu` – fetch menu categories and items for a counter.
- `POST /c/{counter_token}/order` – place an order with a list of items.
- `POST /api/outlet/{tenant}/counters/{order_id}/status` – update an order to `ready` or `delivered`. Marking an order as `delivered` generates an invoice from the dedicated `80mm` series and is suitable for printing on an 80 mm thermal printer.
  The status change is also logged in the tenant audit trail with the acting
  user's identifier.

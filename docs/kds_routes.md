# KDS Routes

Experimental Kitchen Display System endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant_id}/kds/queue | List active orders for the outlet. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/accept | Mark an order as accepted. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/progress | Move an order to in-progress. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/ready | Mark an order as ready. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/serve | Mark an order as served. |

These endpoints rely on tenant databases and are not yet wired into the main application.

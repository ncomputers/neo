# KDS Routes

Experimental Kitchen Display System endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant_id}/kds/queue | List active orders for the outlet and printer agent status. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/accept | Mark an order as accepted. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/progress | Move an order to in-progress. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/ready | Mark an order as ready. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/serve | Mark an order as served. |
| GET | /api/outlet/{tenant_id}/kot/{order_id}.pdf | Printable KOT for an order (PDF/HTML). |

These endpoints rely on tenant databases and are wired into the main application.

The queue endpoint returns a payload:

```json
{
  "ok": true,
  "data": {
    "orders": [],
    "printer_stale": false,
    "retry_queue": 0
  }
}
```

`printer_stale` becomes `true` when the printing bridge fails to send a
heartbeat within a minute. `retry_queue` exposes the length of the bridge's
retry list for basic monitoring.

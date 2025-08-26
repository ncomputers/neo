# KDS Routes

Experimental Kitchen Display System endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant_id}/kds/queue | List active orders for the outlet, printer agent status and delay flag. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/accept | Mark an order as accepted. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/progress | Move an order to in-progress. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/ready | Mark an order as ready. |
| POST | /api/outlet/{tenant_id}/kds/order/{order_id}/serve | Mark an order as served. |
| GET | /api/outlet/{tenant_id}/kds/expo | List ready tickets with aging and allergen badges. |
| POST | /api/outlet/{tenant_id}/kds/expo/{order_id}/picked | Mark a ready order as picked up. |
| POST | /kds/expo/{order_id}/picked | Mark a ready order as picked up. |
| GET | /kds/expo | List ready tickets with aging and allergen badges. |

| GET | /api/outlet/{tenant_id}/kot/{order_id}.pdf | Printable KOT for an order (PDF/HTML). |
| GET | /api/outlet/{tenant_id}/print/status | Printer agent heartbeat and retry queue length. |

These endpoints rely on tenant databases and are wired into the main application.

The `/kds/expo` endpoints resolve the tenant via the `X-Tenant-ID` request header.

The queue endpoint returns a payload:

```json
{
  "ok": true,
  "data": {
    "orders": [],
    "printer_stale": false,
    "retry_queue": 0,
    "kot_delay": false

  }
}
```

`printer_stale` becomes `true` when the printing bridge fails to send a
heartbeat within a minute. `retry_queue` exposes the length of the bridge's
retry list for basic monitoring. `kot_delay` flips to `true` when the oldest
pending order exceeds the SLA, nudging staff when the kitchen falls behind.


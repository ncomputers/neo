from __future__ import annotations

"""Admin route for exporting orders, items and customers."""

from io import BytesIO
from zipfile import ZipFile

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .models_tenant import Customer, MenuItem, Order, OrderItem
from .routes_export_all import _export_table, _iter_bytes
from .routes_exports import DEFAULT_LIMIT, HARD_LIMIT, _session
from .security import ratelimit
from .utils import ratelimits
from .utils.rate_limit import rate_limited

router = APIRouter()


@router.get("/api/admin/export/data.zip")
async def admin_export(
    request: Request, limit: int = DEFAULT_LIMIT, cursor: int | None = None
) -> StreamingResponse:
    """Return a ZIP bundle with order, item and customer data."""

    limit = min(limit, DEFAULT_LIMIT, HARD_LIMIT)
    cur = cursor or 0

    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    policy = ratelimits.exports()
    allowed = await ratelimit.allow(
        redis, ip, "exports", rate_per_min=policy.rate_per_min, burst=policy.burst
    )
    if not allowed:
        retry_after = await redis.ttl(f"ratelimit:{ip}:exports")
        return rate_limited(retry_after)

    tenant_id = request.headers.get("X-Tenant-ID", "demo")
    bundle = BytesIO()
    async with _session(tenant_id) as session:
        with ZipFile(bundle, "w") as zf:
            max_cursor = cur
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    Order,
                    ["id", "table_id", "status", "placed_at"],
                    "orders.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    OrderItem,
                    [
                        "id",
                        "order_id",
                        "item_id",
                        "name_snapshot",
                        "price_snapshot",
                        "qty",
                        "status",
                    ],
                    "order_items.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    MenuItem,
                    [
                        "id",
                        "category_id",
                        "name",
                        "price",
                        "is_veg",
                        "gst_rate",
                        "hsn_sac",
                        "show_fssai",
                        "out_of_stock",
                    ],
                    "items.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    Customer,
                    ["id", "name", "phone"],
                    "customers.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
    headers = {"Content-Disposition": "attachment; filename=export.zip"}
    if cursor and max_cursor != cursor:
        headers["X-Cursor"] = str(max_cursor)
    return StreamingResponse(
        _iter_bytes(bundle), media_type="application/zip", headers=headers
    )

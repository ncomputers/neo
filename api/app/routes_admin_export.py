from __future__ import annotations

"""Admin route for exporting orders, items and customers."""

import asyncio
import csv
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from .models_tenant import Customer, MenuItem, Order, OrderItem
from .routes_export_all import _export_table, _iter_bytes
from .routes_exports import DEFAULT_LIMIT, HARD_LIMIT, SCAN_LIMIT, _session
from .security import ratelimit
from .utils import ratelimits
from .utils.rate_limit import rate_limited

router = APIRouter()

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "exports"


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


async def _run_export(job: str, tenant: str, kind: str, start: str | None, end: str | None, app) -> None:
    """Generate CSV export for ``kind`` and update job status."""
    path = EXPORT_DIR / tenant
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{job}_{kind}.csv"
    async with _session(tenant) as session:
        if kind == "orders":
            cols = [
                ("id", Order.id),
                ("table_id", Order.table_id),
                ("status", Order.status),
                ("placed_at", Order.placed_at),
            ]
            model = Order
            start_dt = datetime.fromisoformat(start) if start else None
            end_dt = datetime.fromisoformat(end) if end else None
        elif kind == "items":
            cols = [
                ("id", MenuItem.id),
                ("name", MenuItem.name),
                ("price", MenuItem.price),
            ]
            model = MenuItem
        elif kind == "customers":
            cols = [
                ("id", Customer.id),
                ("name", Customer.name),
                ("phone", Customer.phone),
            ]
            model = Customer
        else:
            app.state.export_jobs[job] = {"status": "error", "message": "bad type"}
            return
        headers = [c[0] for c in cols]
        select_cols = [c[1] for c in cols]
        last_id = 0
        with file_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            while True:
                stmt = (
                    select(*select_cols)
                    .where(model.id > last_id)
                    .order_by(model.id)
                    .limit(SCAN_LIMIT)
                )
                if kind == "orders":
                    if start_dt:
                        stmt = stmt.where(Order.placed_at >= start_dt)
                    if end_dt:
                        stmt = stmt.where(Order.placed_at <= end_dt)
                rows = (await session.execute(stmt)).all()
                if not rows:
                    break
                for row in rows:
                    writer.writerow(row)
                    last_id = row[0]
                if len(rows) < SCAN_LIMIT:
                    break
    app.state.export_jobs[job] = {
        "status": "complete",
        "url": f"/api/admin/export/{job}/download",
        "path": str(file_path),
        "type": kind,
    }


@router.post("/api/admin/export")
async def request_export(request: Request, payload: dict) -> dict:
    kind = payload.get("type", "")
    job = uuid4().hex
    tenant = request.headers.get("X-Tenant-ID", "demo")
    request.app.state.export_jobs[job] = {"status": "pending", "type": kind}
    asyncio.create_task(_run_export(job, tenant, kind, payload.get("from"), payload.get("to"), request.app))
    return {"job": job}


@router.get("/api/admin/export/{job}")
async def export_status(job: str, request: Request):
    data = request.app.state.export_jobs.get(job)
    if not data:
        raise HTTPException(status_code=404, detail="not found")
    return data


@router.get("/api/admin/export/{job}/download")
async def export_download(job: str, request: Request):
    data = request.app.state.export_jobs.get(job)
    if not data or data.get("status") != "complete":
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(data["path"], filename=f"{data.get('type', 'export')}.csv")

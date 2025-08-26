"""Owner data export route returning a ZIP bundle."""

from __future__ import annotations

import csv
import json
from io import BytesIO, TextIOWrapper
from typing import Iterator
from zipfile import ZipFile

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, case

from .audit import log_event
from .auth import User
from .routes_auth_2fa import stepup_guard
from .models_tenant import (
    Category,
    Customer,
    Invoice,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    TenantMeta,
    Table,
)
from .routes_exports import DEFAULT_LIMIT, SCAN_LIMIT, HARD_LIMIT, _session
from .security import ratelimit
from .utils import ratelimits
from .utils.rate_limit import rate_limited

router = APIRouter()


def _iter_bytes(buffer: BytesIO) -> Iterator[bytes]:
    buffer.seek(0)
    while chunk := buffer.read(8192):
        yield chunk


async def _export_table(
    session,
    model,
    columns,
    filename: str,
    zf: ZipFile,
    limit: int,
    cursor: int,
) -> int:
    headers = [c[0] if isinstance(c, tuple) else c for c in columns]
    exported = 0
    last_id = cursor
    with zf.open(filename, "w") as raw:
        with TextIOWrapper(raw, encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            while exported < limit:
                chunk = min(SCAN_LIMIT, limit - exported)
                select_cols = [
                    c[1] if isinstance(c, tuple) else getattr(model, c) for c in columns
                ]
                stmt = (
                    select(*select_cols)
                    .where(getattr(model, "id") > last_id)
                    .order_by(getattr(model, "id"))
                    .limit(chunk)
                )
                rows = (await session.execute(stmt)).all()
                if not rows:
                    break
                for row in rows:
                    writer.writerow(row)
                    last_id = row[0]
                    exported += 1
                if len(rows) < chunk:
                    break
    return last_id


@router.get("/api/outlet/{tenant_id}/export/all.zip")
async def export_all(
    tenant_id: str,
    request: Request,
    user: User = Depends(stepup_guard("super_admin", "outlet_admin")),
    limit: int = DEFAULT_LIMIT,
    cursor: int | None = None,
) -> StreamingResponse:
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

    bundle = BytesIO()
    async with _session(tenant_id) as session:
        with ZipFile(bundle, "w") as zf:
            max_cursor = cur
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    Category,
                    ["id", "name", "sort"],
                    "menu.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    Table,
                    [
                        ("id", Table.id),
                        ("code", Table.code),
                        ("name", Table.name),
                        (
                            "status",
                            case(
                                (Table.deleted_at.isnot(None), "deleted"),
                                else_="active",
                            ),
                        ),
                    ],
                    "tables.csv",
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
                        ("id", MenuItem.id),
                        ("category_id", MenuItem.category_id),
                        ("name", MenuItem.name),
                        ("price", MenuItem.price),
                        ("is_veg", MenuItem.is_veg),
                        ("gst_rate", MenuItem.gst_rate),
                        ("hsn_sac", MenuItem.hsn_sac),
                        ("show_fssai", MenuItem.show_fssai),
                        ("out_of_stock", MenuItem.out_of_stock),
                        (
                            "status",
                            case(
                                (MenuItem.deleted_at.isnot(None), "deleted"),
                                else_="active",
                            ),
                        ),
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
                    Invoice,
                    ["id", "number", "total", "created_at"],
                    "invoices.csv",
                    zf,
                    limit,
                    cur,
                ),
            )
            max_cursor = max(
                max_cursor,
                await _export_table(
                    session,
                    Payment,
                    ["id", "invoice_id", "mode", "amount", "verified", "created_at"],
                    "payments.csv",
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
            # settings
            settings = await session.execute(select(TenantMeta.menu_version))
            meta_row = settings.first()
            settings_payload = {"menu_version": meta_row[0] if meta_row else 0}
            zf.writestr("settings.json", json.dumps(settings_payload))
            # schema
            schema = {}
            for model in [
                Category,
                MenuItem,
                Order,
                OrderItem,
                Invoice,
                Payment,
                Customer,
                TenantMeta,
            ]:
                schema[model.__tablename__] = {
                    col.name: str(col.type) for col in model.__table__.columns
                }
            zf.writestr("schema.json", json.dumps(schema))

    log_event(user.username, "export_all", tenant_id)

    headers = {"Content-Disposition": "attachment; filename=all.zip"}
    if cursor and max_cursor != cursor:
        headers["X-Cursor"] = str(max_cursor)
    return StreamingResponse(
        _iter_bytes(bundle), media_type="application/zip", headers=headers
    )

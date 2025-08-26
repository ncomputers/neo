from __future__ import annotations

"""Owner-facing export routes."""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.replica import read_only
from .db.tenant import get_engine
from .models_tenant import Invoice
from .security import ratelimit
from .utils import ratelimits
from .utils.rate_limit import rate_limited
from .utils.responses import err

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for the given tenant."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


DEFAULT_LIMIT = int(os.getenv("EXPORT_MAX_ROWS", "10000"))
SCAN_LIMIT = int(os.getenv("EXPORT_SCAN_ROWS", "5000"))
ABSOLUTE_MAX_ROWS = 100_000


def _cap_limit(limit: int) -> tuple[int, bool]:
    """Cap requested limit to hard maximum rows."""
    capped = min(limit, ABSOLUTE_MAX_ROWS)
    return capped, limit > ABSOLUTE_MAX_ROWS


@router.get("/api/outlet/{tenant_id}/exports/daily")
@read_only
async def daily_export(
    tenant_id: str,
    start: str,
    end: str,
    request: Request,
    limit: int = DEFAULT_LIMIT,
    cursor: int | None = None,
    progress: str | None = None,
) -> StreamingResponse:
    """Stream invoice rows as CSV with optional resume and progress."""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid date format")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="invalid range")
    if (end_date - start_date).days > 30:
        return JSONResponse(err("RANGE_TOO_LARGE", "Range too large"), status_code=400)

    limit, capped = _cap_limit(limit)
    cursor = cursor or 0

    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    policy = ratelimits.exports()
    allowed = await ratelimit.allow(
        redis, ip, "exports", rate_per_min=policy.rate_per_min, burst=policy.burst
    )
    if not allowed:
        retry_after = await redis.ttl(f"ratelimit:{ip}:exports")
        return rate_limited(retry_after)

    tz = os.getenv("DEFAULT_TZ", "UTC")
    tzinfo = ZoneInfo(tz)
    start_dt = datetime.combine(start_date, time.min, tzinfo).astimezone(timezone.utc)
    end_dt = datetime.combine(end_date, time.max, tzinfo).astimezone(timezone.utc)

    async with _session(tenant_id) as session:
        last_id = await session.scalar(
            select(Invoice.id)
            .where(
                Invoice.created_at >= start_dt,
                Invoice.created_at <= end_dt,
                Invoice.id > cursor,
            )
            .order_by(Invoice.id)
            .offset(limit - 1)
            .limit(1)
        )
        more = None
        if last_id is not None:
            more = await session.scalar(
                select(Invoice.id)
                .where(
                    Invoice.created_at >= start_dt,
                    Invoice.created_at <= end_dt,
                    Invoice.id > last_id,
                )
                .limit(1)
            )

        async def row_iter():
            exported = 0
            last = cursor
            header = ["id", "no", "date", "subtotal", "tax", "tip", "total", "settled"]
            yield ",".join(header) + "\n"
            while exported < limit:
                chunk = min(SCAN_LIMIT, limit - exported)
                conditions = [
                    Invoice.created_at >= start_dt,
                    Invoice.created_at <= end_dt,
                    Invoice.id > last,
                ]
                if last_id is not None:
                    conditions.append(Invoice.id <= last_id)
                stmt = (
                    select(
                        Invoice.id,
                        Invoice.number,
                        Invoice.bill_json,
                        Invoice.tip,
                        Invoice.total,
                        Invoice.settled,
                        Invoice.created_at,
                    )
                    .where(*conditions)
                    .order_by(Invoice.id)
                    .limit(chunk)
                )
                rows = (await session.execute(stmt)).all()
                if not rows:
                    break
                for (
                    inv_id,
                    number,
                    bill,
                    tip,
                    total_amt,
                    settled,
                    created_at,
                ) in rows:
                    inv_date = created_at.astimezone(tzinfo).date().isoformat()
                    subtotal = bill.get("subtotal", 0)
                    tax = sum(bill.get("tax_breakup", {}).values())
                    line = f"{inv_id},{number},{inv_date},{subtotal},{tax},{float(tip or 0)},{float(total_amt)},{settled}\n"
                    yield line
                    exported += 1
                    last = inv_id
                    if progress:
                        request.app.state.export_progress[progress] = exported
                if len(rows) < chunk or (last_id and last >= last_id):
                    break
            if progress:
                request.app.state.export_progress.pop(progress, None)

        headers = {"Content-Disposition": "attachment; filename=invoices.csv"}
        if more is not None:
            headers["X-Cursor"] = str(last_id)
        if capped:
            headers["X-Export-Hint"] = f"row cap {ABSOLUTE_MAX_ROWS}"
        return StreamingResponse(row_iter(), media_type="text/csv", headers=headers)


@router.get("/api/outlet/{tenant_id}/exports/progress/{progress_id}")
async def export_progress(
    tenant_id: str, progress_id: str, request: Request
) -> StreamingResponse:
    """Server-sent events stream of export progress."""

    async def event_gen():
        last = -1
        while True:
            val = request.app.state.export_progress.get(progress_id)
            if val is None:
                break
            if val != last:
                yield f"data: {val}\n\n"
                last = val
            await asyncio.sleep(1)

    return StreamingResponse(event_gen(), media_type="text/event-stream")

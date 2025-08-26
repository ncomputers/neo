from __future__ import annotations

"""Accounting export routes."""

import csv
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import Invoice

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for ``tenant_id``."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.get("/api/outlet/{tenant_id}/accounting/sales_register.csv")
async def sales_register_csv(
    tenant_id: str,
    from_: str = Query(alias="from"),
    to: str = Query(alias="to"),
    composition: bool = False,
) -> Response:
    """Return a CSV sales register for the given date range."""
    try:
        start_dt = datetime.strptime(from_, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(to, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ) + timedelta(days=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date") from exc
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="invalid range")

    async with _session(tenant_id) as session:
        rows = (
            await session.execute(
                select(
                    Invoice.number, Invoice.bill_json, Invoice.total, Invoice.created_at
                )
                .where(Invoice.created_at >= start_dt, Invoice.created_at < end_dt)
                .order_by(Invoice.id)
            )
        ).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "invoice_no", "subtotal", "tax", "total"])
    for number, bill, total, created_at in rows:
        subtotal = bill.get("subtotal", 0)
        if composition:
            tax = 0
            grand_total = subtotal
        else:
            tax = sum((bill.get("tax_breakup") or {}).values())
            grand_total = float(total)
        writer.writerow(
            [
                created_at.date().isoformat(),
                number,
                f"{subtotal:.1f}",
                f"{tax:.1f}",
                f"{grand_total:.1f}",
            ]
        )

    resp = Response(content=output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=sales_register.csv"
    return resp


@router.get("/api/outlet/{tenant_id}/accounting/gst_summary.csv")
async def gst_summary_csv(
    tenant_id: str,
    from_: str = Query(alias="from"),
    to: str = Query(alias="to"),
    composition: bool = False,
) -> Response:
    """Return a CSV GST summary for the given date range."""
    try:
        start_dt = datetime.strptime(from_, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(to, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ) + timedelta(days=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date") from exc
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="invalid range")

    async with _session(tenant_id) as session:
        results = (
            (
                await session.execute(
                    select(Invoice.gst_breakup).where(
                        Invoice.created_at >= start_dt, Invoice.created_at < end_dt
                    )
                )
            )
            .scalars()
            .all()
        )

    summary: dict[str, dict[str, Decimal]] = {}
    for breakup in results:
        if not breakup:
            continue
        for rate, tax in breakup.items():
            rate_str = str(rate)
            tax_val = Decimal(str(tax))
            taxable = (
                tax_val * Decimal("100") / Decimal(str(rate))
                if not composition
                else Decimal("0")
            )
            entry = summary.setdefault(
                rate_str,
                {
                    "taxable": Decimal("0"),
                    "cgst": Decimal("0"),
                    "sgst": Decimal("0"),
                    "igst": Decimal("0"),
                },
            )
            if composition:
                entry["taxable"] += taxable
                continue
            half = tax_val / Decimal("2")
            entry["taxable"] += taxable
            entry["cgst"] += half
            entry["sgst"] += half

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["gst_rate", "taxable_value", "cgst", "sgst", "igst", "total"])
    for rate in sorted(summary.keys(), key=lambda r: Decimal(r)):
        vals = summary[rate]
        total = vals["taxable"] + vals["cgst"] + vals["sgst"] + vals["igst"]
        writer.writerow(
            [
                rate,
                f"{vals['taxable']:.1f}",
                f"{vals['cgst']:.1f}",
                f"{vals['sgst']:.1f}",
                f"{vals['igst']:.1f}",
                f"{total:.1f}",
            ]
        )

    resp = Response(content=output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=gst_summary.csv"
    return resp

from __future__ import annotations

"""Routes exporting accounting-friendly CSVs."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
import csv

from fastapi import APIRouter, HTTPException, Response, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import Invoice, MenuItem, OrderItem



router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


def _parse_range(from_: str, to: str) -> tuple[datetime, datetime]:
    try:
        start = datetime.strptime(from_, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="invalid date") from exc
    if end <= start:
        raise HTTPException(status_code=400, detail="invalid range")
    return start, end


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/api/outlet/{tenant_id}/accounting/sales_register.csv")
async def sales_register_csv(
    tenant_id: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(..., alias="to"),
    composition: bool = False,
) -> Response:
    """Return per-invoice sales with GST split for the date range."""

    start, end = _parse_range(from_, to)

    async with _session(tenant_id) as session:
        result = await session.execute(
            select(Invoice.number, Invoice.created_at, Invoice.bill_json)
            .where(Invoice.created_at >= start, Invoice.created_at < end)
            .order_by(Invoice.id)
        )
        rows = result.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "invoice_no", "subtotal", "tax", "total"])

    total_subtotal = Decimal("0")
    total_tax = Decimal("0")

    for number, created_at, bill in rows:
        subtotal = float(bill.get("subtotal", 0))
        tax_breakup = bill.get("tax_breakup", {})
        tax = 0.0 if composition else float(sum(tax_breakup.values()))
        total = float(bill.get("total", subtotal + tax))

        total_subtotal += Decimal(str(subtotal))
        total_tax += Decimal(str(tax))

        writer.writerow(
            [
                created_at.date().isoformat(),
                number,
                str(subtotal),
                str(tax),
                str(total),
            ]
        )

    grand_total = total_subtotal + total_tax
    writer.writerow(
        [
            "TOTAL",
            "",
            str(float(total_subtotal)),
            str(float(total_tax)),
            str(float(grand_total)),
        ]
    )

    resp = Response(content=output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=sales_register.csv"
    return resp


@router.get("/api/outlet/{tenant_id}/accounting/gst_summary.csv")
async def gst_summary_csv(
    tenant_id: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(..., alias="to"),
    composition: bool = False,
) -> Response:
    """Return a GST summary grouped by HSN for the date range."""

    start, end = _parse_range(from_, to)

    async with _session(tenant_id) as session:
        result = await session.execute(
            select(
                MenuItem.gst_rate,
                OrderItem.qty,
                OrderItem.price_snapshot,
                Invoice.bill_json,
            )
            .join(Invoice, Invoice.order_group_id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.item_id)
            .where(Invoice.created_at >= start, Invoice.created_at < end)
        )
        rows = result.all()

    summary: dict[str, dict[str, Decimal]] = {}
    for gst_rate, qty, price, bill in rows:
        qty_d = Decimal(str(qty))
        price_d = Decimal(str(price))
        taxable = _round(qty_d * price_d)
        rate = Decimal(str(gst_rate or 0))

        if composition or rate == 0:
            cgst = sgst = igst = Decimal("0")
        else:
            if bill.get("inter_state"):
                igst = _round(taxable * rate / Decimal("100"))
                cgst = sgst = Decimal("0")
            else:
                cgst = _round(taxable * rate / Decimal("200"))
                sgst = cgst
                igst = Decimal("0")

        rate_key = str(int(rate)) if rate == int(rate) else str(rate)
        key = rate_key
        entry = summary.setdefault(
            key,
            {"taxable": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0"), "igst": Decimal("0")},
        )
        entry["taxable"] += taxable
        entry["cgst"] += cgst
        entry["sgst"] += sgst
        entry["igst"] += igst

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["gst_rate", "taxable_value", "cgst", "sgst", "igst", "total"])

    for rate in sorted(summary.keys(), key=lambda r: float(r)):
        vals = summary[rate]
        total = vals["taxable"] + vals["cgst"] + vals["sgst"] + vals["igst"]
        writer.writerow(
            [
                rate,
                str(float(vals["taxable"])),
                str(float(vals["cgst"])),
                str(float(vals["sgst"])),
                str(float(vals["igst"])),
                str(float(total)),

            ]
        )

    resp = Response(content=output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=gst_summary.csv"
    return resp


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
    """Return line-item sales with GST split for the date range."""

    start, end = _parse_range(from_, to)

    async with _session(tenant_id) as session:
        result = await session.execute(
            select(
                Invoice.number,
                Invoice.created_at,
                Invoice.bill_json,
                OrderItem.name_snapshot,
                OrderItem.qty,
                OrderItem.price_snapshot,
                MenuItem.hsn_sac,
                MenuItem.gst_rate,
            )
            .join(OrderItem, Invoice.order_group_id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.item_id)
            .where(Invoice.created_at >= start, Invoice.created_at < end)
            .order_by(Invoice.id, OrderItem.id)
        )
        rows = result.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "date",
            "invoice_no",
            "item",
            "hsn",
            "qty",
            "price",
            "taxable_value",
            "cgst",
            "sgst",
            "igst",
            "total",
        ]
    )

    total_taxable = Decimal("0")
    total_cgst = Decimal("0")
    total_sgst = Decimal("0")
    total_igst = Decimal("0")

    for number, created_at, bill, name, qty, price, hsn, gst_rate in rows:
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

        line_total = taxable + cgst + sgst + igst

        total_taxable += taxable
        total_cgst += cgst
        total_sgst += sgst
        total_igst += igst

        writer.writerow(
            [
                created_at.date().isoformat(),
                number,
                name,
                hsn or "",
                str(qty),
                f"{price_d:.2f}",
                f"{taxable:.2f}",
                f"{cgst:.2f}",
                f"{sgst:.2f}",
                f"{igst:.2f}",
                f"{line_total:.2f}",
            ]
        )

    grand_total = total_taxable + total_cgst + total_sgst + total_igst
    writer.writerow(
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            "",
            f"{total_taxable:.2f}",
            f"{total_cgst:.2f}",
            f"{total_sgst:.2f}",
            f"{total_igst:.2f}",
            f"{grand_total:.2f}",
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
                MenuItem.hsn_sac,
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
    for hsn, gst_rate, qty, price, bill in rows:
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

        key = hsn or ""
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
    writer.writerow(["hsn", "taxable_value", "cgst", "sgst", "igst", "total"])

    for hsn in sorted(summary.keys()):
        vals = summary[hsn]
        total = vals["taxable"] + vals["cgst"] + vals["sgst"] + vals["igst"]
        writer.writerow(
            [
                hsn,
                f"{vals['taxable']:.2f}",
                f"{vals['cgst']:.2f}",
                f"{vals['sgst']:.2f}",
                f"{vals['igst']:.2f}",
                f"{total:.2f}",

            ]
        )

    resp = Response(content=output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=gst_summary.csv"
    return resp


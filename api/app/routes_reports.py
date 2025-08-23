from __future__ import annotations

"""Reporting routes for daily closing reports."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from io import StringIO
import csv
import os

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import Invoice, MenuItem, OrderItem
from .repos_sqlalchemy import invoices_repo_sql
from .services import notifications

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


@router.get("/api/outlet/{tenant_id}/reports/z")
async def daily_z_report(tenant_id: str, date: str, format: str = "csv"):
    """Return a daily Z-report for ``date`` in CSV format."""
    if format != "csv":
        raise HTTPException(status_code=400, detail="unsupported format")
    tz = os.getenv("DEFAULT_TZ", "UTC")
    day = datetime.strptime(date, "%Y-%m-%d").date()
    async with _session(tenant_id) as session:
        rows = await invoices_repo_sql.list_day(session, day, tz)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["invoice_no", "subtotal", "tax", "total", "payments", "settled"])
    for row in rows:
        payments = ";".join(f"{p['mode']}:{p['amount']}" for p in row["payments"])
        writer.writerow(
            [row["number"], row["subtotal"], row["tax"], row["total"], payments, row["settled"]]
        )
    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=z-report.csv"
    await notifications.enqueue(tenant_id, "day.close", {"date": date})
    return response


@router.get("/api/outlet/{tenant_id}/reports/gst/monthly")
async def gst_monthly_report(
    tenant_id: str, month: str, gst_mode: str = "reg"
):
    """Return a GST-aware monthly summary for ``month``.

    Parameters
    ----------
    tenant_id:
        Identifier for the tenant/outlet.
    month:
        Target month in ``YYYY-MM`` format.
    gst_mode:
        GST registration mode: ``reg``, ``comp`` or ``unreg``. Default ``reg``.
    """

    try:
        start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="invalid month") from exc

    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    async with _session(tenant_id) as session:
        result = await session.execute(
            select(
                MenuItem.hsn_sac,
                MenuItem.gst_rate,
                OrderItem.qty,
                OrderItem.price_snapshot,
            )
            .join(Invoice, Invoice.order_group_id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.item_id)
            .where(Invoice.created_at >= start, Invoice.created_at < end)
        )
        rows = result.all()

    output = StringIO()
    writer = csv.writer(output)

    if gst_mode == "reg":
        summary: dict[str, dict[str, Decimal]] = {}
        for hsn, gst_rate, qty, price in rows:
            taxable = Decimal(str(qty)) * Decimal(str(price))
            rate = Decimal(str(gst_rate or 0))
            cgst = taxable * rate / Decimal("200")
            sgst = cgst
            key = hsn or ""
            entry = summary.setdefault(
                key, {"taxable": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
            )
            entry["taxable"] += taxable
            entry["cgst"] += cgst
            entry["sgst"] += sgst

        writer.writerow(["hsn", "taxable_value", "cgst", "sgst", "total"])
        total_taxable = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        for hsn in sorted(summary.keys()):
            vals = summary[hsn]
            total = vals["taxable"] + vals["cgst"] + vals["sgst"]
            writer.writerow(
                [
                    hsn,
                    f"{vals['taxable']:.1f}",
                    f"{vals['cgst']:.1f}",
                    f"{vals['sgst']:.1f}",
                    f"{total:.1f}",
                ]
            )
            total_taxable += vals["taxable"]
            total_cgst += vals["cgst"]
            total_sgst += vals["sgst"]
        grand_total = total_taxable + total_cgst + total_sgst
        writer.writerow(
            [
                "TOTAL",
                f"{total_taxable:.1f}",
                f"{total_cgst:.1f}",
                f"{total_sgst:.1f}",
                f"{grand_total:.1f}",
            ]
        )
    elif gst_mode == "comp":
        subtotal = sum(
            Decimal(str(qty)) * Decimal(str(price)) for _, _, qty, price in rows
        )
        writer.writerow(["description", "taxable_value", "total"])
        writer.writerow(["Total", f"{subtotal:.1f}", f"{subtotal:.1f}"])
    else:  # unregistered
        total = sum(
            Decimal(str(qty)) * Decimal(str(price)) for _, _, qty, price in rows
        )
        writer.writerow(["description", "total"])
        writer.writerow(["Total", f"{total:.1f}"])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=gst-report.csv"
    return response

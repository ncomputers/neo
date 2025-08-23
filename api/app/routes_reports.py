from __future__ import annotations

"""Reporting routes for daily closing reports."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta, time
from decimal import Decimal
from io import StringIO
import csv
import os

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select, func, desc
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import Invoice, MenuItem, OrderItem, Order
from .repos_sqlalchemy import invoices_repo_sql
from .services import notifications
from .pdf.render import render_template

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


@router.get("/api/outlet/{tenant_id}/reports/daybook.pdf")
async def owner_daybook_pdf(tenant_id: str, date: str):
    """Return a daily owner daybook in PDF or HTML format."""

    tz = os.getenv("DEFAULT_TZ", "UTC")
    day = datetime.strptime(date, "%Y-%m-%d").date()
    async with _session(tenant_id) as session:
        rows = await invoices_repo_sql.list_day(session, day, tz)

        tzinfo = ZoneInfo(tz)
        start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
        end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)
        result = await session.execute(
            select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.placed_at >= start, Order.placed_at <= end)
            .group_by(OrderItem.name_snapshot)
            .order_by(desc("qty"))
            .limit(5)
        )
        top_items = [{"name": name, "qty": int(qty)} for name, qty in result.all()]

    orders = len(rows)
    subtotal = sum(r["subtotal"] for r in rows)
    tax = sum(r["tax"] for r in rows)
    tip = sum(r["tip"] for r in rows)
    total = sum(r["total"] for r in rows)
    payments: dict[str, float] = {}
    for r in rows:
        for p in r["payments"]:
            payments[p["mode"]] = payments.get(p["mode"], 0) + p["amount"]

    content, mimetype = render_template(
        "daybook_a4.html",
        {
            "date": date,
            "orders": orders,
            "subtotal": subtotal,
            "tax": tax,
            "tip": tip,
            "total": total,
            "payments": payments,
            "top_items": top_items,
        },
    )
    response = Response(content=content, media_type=mimetype)
    ext = "pdf" if mimetype == "application/pdf" else "html"
    response.headers["Content-Disposition"] = f"attachment; filename=daybook.{ext}"
    return response


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

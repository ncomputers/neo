from __future__ import annotations

"""Owner-facing export routes."""

from contextlib import asynccontextmanager
from datetime import datetime, date, time, timedelta, timezone
from io import StringIO, BytesIO
import csv
import os
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zoneinfo import ZoneInfo

from .db.tenant import get_engine
from .models_tenant import Invoice, Payment
from .repos_sqlalchemy import invoices_repo_sql
from .pdf.render import render_invoice
from .utils.responses import err

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for the given tenant."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


DEFAULT_LIMIT = int(os.getenv("EXPORT_MAX_ROWS", "10000"))


@router.get("/api/outlet/{tenant_id}/exports/daily")
async def daily_export(
    tenant_id: str, start: str, end: str, limit: int = DEFAULT_LIMIT
) -> Response:
    """Return a ZIP bundle of invoices, payments and z-report rows."""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid date format")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="invalid range")
    if (end_date - start_date).days > 30:
        return JSONResponse(err("RANGE_TOO_LARGE", "Range too large"), status_code=400)

    limit = min(limit, DEFAULT_LIMIT)

    tz = os.getenv("DEFAULT_TZ", "UTC")
    tzinfo = ZoneInfo(tz)
    start_dt = datetime.combine(start_date, time.min, tzinfo).astimezone(timezone.utc)
    end_dt = datetime.combine(end_date, time.max, tzinfo).astimezone(timezone.utc)

    async with _session(tenant_id) as session:
        inv_rows = (
            await session.execute(
                select(
                    Invoice.id,
                    Invoice.number,
                    Invoice.bill_json,
                    Invoice.tip,
                    Invoice.total,
                    Invoice.settled,
                    Invoice.created_at,
                )
                .where(Invoice.created_at >= start_dt, Invoice.created_at <= end_dt)
                .limit(limit)
            )
        ).all()

        pay_rows = (
            await session.execute(
                select(
                    Payment.invoice_id,
                    Payment.mode,
                    Payment.amount,
                    Payment.utr,
                    Payment.verified,
                    Payment.created_at,
                )
                .join(Invoice, Payment.invoice_id == Invoice.id)
                .where(Invoice.created_at >= start_dt, Invoice.created_at <= end_dt)
                .limit(limit)
            )
        ).all()

        invoices_csv = StringIO()
        inv_writer = csv.writer(invoices_csv)
        inv_writer.writerow(["id", "no", "date", "subtotal", "tax", "tip", "total", "settled"])
        for inv_id, number, bill, tip, total, settled, created_at in inv_rows:
            inv_date = created_at.astimezone(tzinfo).date().isoformat()
            subtotal = bill.get("subtotal", 0)
            tax = sum(bill.get("tax_breakup", {}).values())
            inv_writer.writerow(
                [
                    inv_id,
                    number,
                    inv_date,
                    subtotal,
                    tax,
                    float(tip or 0),
                    float(total),
                    settled,
                ]
            )

        payments_csv = StringIO()
        pay_writer = csv.writer(payments_csv)
        pay_writer.writerow(["invoice_id", "mode", "amount", "utr", "verified", "ts"])
        for invoice_id, mode, amount, utr, verified, created_at in pay_rows:
            ts = created_at.astimezone(tzinfo).isoformat()
            pay_writer.writerow(
                [invoice_id, mode, float(amount), utr, verified, ts]
            )

        z_csv = StringIO()
        z_writer = csv.writer(z_csv)
        z_writer.writerow(["date", "orders", "sales", "tax", "cash", "upi", "card"])
        day = start_date
        try:
            while day <= end_date:
                rows = await invoices_repo_sql.list_day(session, day, tz, tenant_id)
                orders = len(rows)
                sales = sum(r["total"] for r in rows)
                tax_total = sum(r["tax"] for r in rows)
                cash = sum(
                    p["amount"] for r in rows for p in r["payments"] if p["mode"] == "cash"
                )
                upi = sum(
                    p["amount"] for r in rows for p in r["payments"] if p["mode"] == "upi"
                )
                card = sum(
                    p["amount"] for r in rows for p in r["payments"] if p["mode"] == "card"
                )
                z_writer.writerow([day.isoformat(), orders, sales, tax_total, cash, upi, card])
                day += timedelta(days=1)
        except PermissionError:
            raise HTTPException(status_code=403, detail="forbidden") from None

        bundle = BytesIO()
        with ZipFile(bundle, "w") as zf:
            zf.writestr("invoices.csv", invoices_csv.getvalue())
            zf.writestr("payments.csv", payments_csv.getvalue())
            zf.writestr("z-report.csv", z_csv.getvalue())
            for _id, number, bill, *_rest in inv_rows:
                content, mimetype = render_invoice(bill, size="80mm")
                ext = "pdf" if mimetype == "application/pdf" else "html"
                zf.writestr(f"invoices/{number}.{ext}", content)

    response = Response(bundle.getvalue(), media_type="application/zip")
    response.headers["Content-Disposition"] = "attachment; filename=export.zip"
    return response

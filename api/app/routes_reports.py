from __future__ import annotations

from __future__ import annotations

"""Reporting routes for daily closing reports."""

from contextlib import asynccontextmanager
from datetime import datetime
from io import StringIO
import csv
import os

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
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



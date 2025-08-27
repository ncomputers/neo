from __future__ import annotations

"""Privacy DSAR endpoints for data principals."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .db import SessionLocal
from .utils.audit import audit
from .utils.responses import ok
from .utils.sql import build_where_clause

router = APIRouter()


class DSARRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    dry_run: bool = False


@router.post("/privacy/dsar/export")
@audit("dsar_export", {"phone", "email"})
async def dsar_export(payload: DSARRequest) -> dict:
    filters = payload.dict(exclude_none=True, exclude={"dry_run"})
    if not filters:
        raise HTTPException(status_code=400, detail="phone or email required")
    where_sql, where_params = build_where_clause(filters)
    with SessionLocal() as session:
        stmt = text(
            "SELECT id, name, phone, email, created_at, allow_analytics, allow_wa FROM customers WHERE "
            + where_sql
        ).bindparams(**where_params)  # nosec B608
        cust_rows = session.execute(stmt).mappings().all()
        stmt = text(
            "SELECT id, name, phone, email, created_at FROM invoices WHERE " + where_sql
        ).bindparams(**where_params)  # nosec B608
        inv_rows = session.execute(stmt).mappings().all()
        stmt = text(
            "SELECT p.id, p.invoice_id, p.mode, p.amount, NULL as utr, p.verified, p.created_at "
            "FROM payments p JOIN invoices i ON p.invoice_id = i.id WHERE " + where_sql
        ).bindparams(**where_params)  # nosec B608
        pay_rows = session.execute(stmt).mappings().all()
    return ok(
        {
            "customers": [dict(r) for r in cust_rows],
            "invoices": [dict(r) for r in inv_rows],
            "payments": [dict(r) for r in pay_rows],
        }
    )


@router.post("/privacy/dsar/delete")
@audit("dsar_delete", {"phone", "email"})
async def dsar_delete(payload: DSARRequest) -> dict:
    filters = payload.dict(exclude_none=True, exclude={"dry_run"})
    if not filters:
        raise HTTPException(status_code=400, detail="phone or email required")
    where_sql, where_params = build_where_clause(filters)
    with SessionLocal() as session:
        if payload.dry_run:
            stmt = text(
                "SELECT COUNT(*) FROM customers WHERE " + where_sql
            ).bindparams(**where_params)  # nosec B608
            cust_count = session.execute(stmt).scalar()
            stmt = text(
                "SELECT COUNT(*) FROM invoices WHERE " + where_sql
            ).bindparams(**where_params)  # nosec B608
            inv_count = session.execute(stmt).scalar()
            stmt = text(
                "SELECT COUNT(*) FROM payments p JOIN invoices i ON p.invoice_id = i.id WHERE "
                + where_sql
            ).bindparams(**where_params)  # nosec B608
            pay_count = session.execute(stmt).scalar()
        else:
            stmt = text(
                "UPDATE payments SET utr = NULL WHERE invoice_id IN (SELECT id FROM invoices WHERE "
                + where_sql
                + ")"
            ).bindparams(**where_params)  # nosec B608
            pay_res = session.execute(stmt)
            stmt = text(
                "UPDATE invoices SET name = NULL, phone = NULL, email = NULL WHERE "
                + where_sql
            ).bindparams(**where_params)  # nosec B608
            inv_res = session.execute(stmt)
            stmt = text(
                "UPDATE customers SET name = NULL, phone = NULL, email = NULL, allow_analytics = 0, allow_wa = 0 WHERE "
                + where_sql
            ).bindparams(**where_params)  # nosec B608
            cust_res = session.execute(stmt)
            pay_count = pay_res.rowcount or 0
            inv_count = inv_res.rowcount or 0
            cust_count = cust_res.rowcount or 0
            session.commit()
    return ok(
        {
            "customers": cust_count,
            "invoices": inv_count,
            "payments": pay_count,
            "dry_run": payload.dry_run,
        }
    )


__all__ = ["router"]

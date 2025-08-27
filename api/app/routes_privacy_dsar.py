from __future__ import annotations

"""Privacy DSAR endpoints for data principals.

SQLAlchemy expressions are used to avoid unsafe string concatenation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import column, func, literal, select, table, update

from .db import SessionLocal
from .utils.audit import audit
from .utils.responses import ok
from .utils.sql import build_where_clause

router = APIRouter()

customers = table(
    "customers",
    column("id"),
    column("name"),
    column("phone"),
    column("email"),
    column("allow_analytics"),
    column("allow_wa"),
    column("created_at"),
)

invoices = table(
    "invoices",
    column("id"),
    column("name"),
    column("phone"),
    column("email"),
    column("created_at"),
)

payments = table(
    "payments",
    column("id"),
    column("invoice_id"),
    column("mode"),
    column("amount"),
    column("utr"),
    column("verified"),
    column("created_at"),
)


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
    where_clause = build_where_clause(filters)
    with SessionLocal() as session:
        cust_stmt = select(
            customers.c.id,
            customers.c.name,
            customers.c.phone,
            customers.c.email,
            customers.c.created_at,
            customers.c.allow_analytics,
            customers.c.allow_wa,
        ).where(where_clause)
        cust_rows = session.execute(cust_stmt).mappings().all()
        inv_stmt = select(
            invoices.c.id,
            invoices.c.name,
            invoices.c.phone,
            invoices.c.email,
            invoices.c.created_at,
        ).where(where_clause)
        inv_rows = session.execute(inv_stmt).mappings().all()
        pay_stmt = (
            select(
                payments.c.id,
                payments.c.invoice_id,
                payments.c.mode,
                payments.c.amount,
                literal(None).label("utr"),
                payments.c.verified,
                payments.c.created_at,
            )
            .select_from(
                payments.join(invoices, payments.c.invoice_id == invoices.c.id)
            )
            .where(where_clause)
        )
        pay_rows = session.execute(pay_stmt).mappings().all()
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
    where_clause = build_where_clause(filters)
    with SessionLocal() as session:
        if payload.dry_run:
            cust_stmt = select(func.count()).select_from(customers).where(where_clause)
            cust_count = session.execute(cust_stmt).scalar()
            inv_stmt = select(func.count()).select_from(invoices).where(where_clause)
            inv_count = session.execute(inv_stmt).scalar()
            pay_stmt = (
                select(func.count())
                .select_from(
                    payments.join(invoices, payments.c.invoice_id == invoices.c.id)
                )
                .where(where_clause)
            )
            pay_count = session.execute(pay_stmt).scalar()
        else:
            pay_stmt = (
                update(payments)
                .where(
                    payments.c.invoice_id.in_(select(invoices.c.id).where(where_clause))
                )
                .values(utr=None)
            )
            pay_res = session.execute(pay_stmt)
            inv_stmt = (
                update(invoices)
                .where(where_clause)
                .values(name=None, phone=None, email=None)
            )
            inv_res = session.execute(inv_stmt)
            cust_stmt = (
                update(customers)
                .where(where_clause)
                .values(
                    name=None, phone=None, email=None, allow_analytics=0, allow_wa=0
                )
            )
            cust_res = session.execute(cust_stmt)
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

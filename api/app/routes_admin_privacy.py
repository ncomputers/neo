from __future__ import annotations

"""Admin privacy routes for DSAR export and delete.

Queries now use SQLAlchemy expressions to avoid string concatenation vulnerabilities.
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import column, func, select, table, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
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


class DSARRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    dry_run: bool = False


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.post("/api/outlet/{tenant_id}/privacy/dsar/export")
@audit("dsar_export", {"phone", "email"})
async def dsar_export(
    tenant_id: str,
    payload: DSARRequest,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    filters = payload.dict(exclude_none=True, exclude={"dry_run"})
    if not filters:
        raise HTTPException(status_code=400, detail="phone or email required")
    where_clause = build_where_clause(filters)
    async with _session(tenant_id) as session:
        cust_stmt = select(
            customers.c.id,
            customers.c.name,
            customers.c.phone,
            customers.c.email,
            customers.c.created_at,
        ).where(where_clause)
        cust_rows = (await session.execute(cust_stmt)).mappings().all()
        inv_stmt = select(
            invoices.c.id,
            invoices.c.name,
            invoices.c.phone,
            invoices.c.email,
            invoices.c.created_at,
        ).where(where_clause)
        inv_rows = (await session.execute(inv_stmt)).mappings().all()
    return ok(
        {
            "customers": [dict(r) for r in cust_rows],
            "invoices": [dict(r) for r in inv_rows],
        }
    )


@router.post("/api/outlet/{tenant_id}/privacy/dsar/delete")
@audit("dsar_delete", {"phone", "email"})
async def dsar_delete(
    tenant_id: str,
    payload: DSARRequest,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    filters = payload.dict(exclude_none=True, exclude={"dry_run"})
    if not filters:
        raise HTTPException(status_code=400, detail="phone or email required")
    where_clause = build_where_clause(filters)
    async with _session(tenant_id) as session:
        if payload.dry_run:
            cust_stmt = select(func.count()).select_from(customers).where(where_clause)
            cust_count = (await session.execute(cust_stmt)).scalar()
            inv_stmt = select(func.count()).select_from(invoices).where(where_clause)
            inv_count = (await session.execute(inv_stmt)).scalar()
        else:
            cust_stmt = (
                update(customers)
                .where(where_clause)
                .values(name=None, phone=None, email=None)
            )
            cust_res = await session.execute(cust_stmt)
            inv_stmt = (
                update(invoices)
                .where(where_clause)
                .values(name=None, phone=None, email=None)
            )
            inv_res = await session.execute(inv_stmt)
            cust_count = cust_res.rowcount or 0
            inv_count = inv_res.rowcount or 0
            await session.commit()
    return ok(
        {"customers": cust_count, "invoices": inv_count, "dry_run": payload.dry_run}
    )


__all__ = ["router"]

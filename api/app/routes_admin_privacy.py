from __future__ import annotations

"""Admin privacy routes for DSAR export and delete."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .utils.audit import audit
from .utils.responses import ok
from .utils.sql import build_where_clause

router = APIRouter()


class DSARRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    dry_run: bool = False


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
    where_sql, where_params = build_where_clause(filters)
    async with _session(tenant_id) as session:
        stmt = text(
            "SELECT id, name, phone, email, created_at FROM customers WHERE " + where_sql
        ).bindparams(**where_params)  # nosec B608
        cust_rows = (await session.execute(stmt)).mappings().all()
        stmt = text(
            "SELECT id, name, phone, email, created_at FROM invoices WHERE " + where_sql
        ).bindparams(**where_params)  # nosec B608
        inv_rows = (await session.execute(stmt)).mappings().all()
    return ok({"customers": [dict(r) for r in cust_rows], "invoices": [dict(r) for r in inv_rows]})


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
    where_sql, where_params = build_where_clause(filters)
    async with _session(tenant_id) as session:
        if payload.dry_run:
            stmt = text(
                "SELECT COUNT(*) FROM customers WHERE " + where_sql
            ).bindparams(**where_params)  # nosec B608
            cust_count = (await session.execute(stmt)).scalar()
            stmt = text(
                "SELECT COUNT(*) FROM invoices WHERE " + where_sql
            ).bindparams(**where_params)  # nosec B608
            inv_count = (await session.execute(stmt)).scalar()
        else:
            stmt = text(
                "UPDATE customers SET name = NULL, phone = NULL, email = NULL WHERE "
                + where_sql
            ).bindparams(**where_params)  # nosec B608
            cust_res = await session.execute(stmt)
            stmt = text(
                "UPDATE invoices SET name = NULL, phone = NULL, email = NULL WHERE "
                + where_sql
            ).bindparams(**where_params)  # nosec B608
            inv_res = await session.execute(stmt)
            cust_count = cust_res.rowcount or 0
            inv_count = inv_res.rowcount or 0
            await session.commit()
    return ok({"customers": cust_count, "invoices": inv_count, "dry_run": payload.dry_run})


__all__ = ["router"]

from __future__ import annotations

"""Admin privacy routes for DSAR export and delete."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


class DSARRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    dry_run: bool = False

    def filters(self) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if self.phone:
            clauses.append("phone = :phone")
            params["phone"] = self.phone
        if self.email:
            clauses.append("email = :email")
            params["email"] = self.email
        if not clauses:
            raise HTTPException(status_code=400, detail="phone or email required")
        return " OR ".join(clauses), params


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
@audit("dsar_export")
async def dsar_export(
    tenant_id: str,
    payload: DSARRequest,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    clause, params = payload.filters()
    async with _session(tenant_id) as session:
        cust_rows = (
            await session.execute(
                text(
                    f"SELECT id, name, phone, email, created_at FROM customers WHERE {clause}"
                ),
                params,
            )
        ).mappings().all()
        inv_rows = (
            await session.execute(
                text(
                    f"SELECT id, name, phone, email, created_at FROM invoices WHERE {clause}"
                ),
                params,
            )
        ).mappings().all()
    return ok({"customers": [dict(r) for r in cust_rows], "invoices": [dict(r) for r in inv_rows]})


@router.post("/api/outlet/{tenant_id}/privacy/dsar/delete")
@audit("dsar_delete")
async def dsar_delete(
    tenant_id: str,
    payload: DSARRequest,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    clause, params = payload.filters()
    async with _session(tenant_id) as session:
        if payload.dry_run:
            cust_count = (
                await session.execute(
                    text(f"SELECT COUNT(*) FROM customers WHERE {clause}"), params
                )
            ).scalar()
            inv_count = (
                await session.execute(
                    text(f"SELECT COUNT(*) FROM invoices WHERE {clause}"), params
                )
            ).scalar()
        else:
            cust_res = await session.execute(
                text(
                    f"UPDATE customers SET name = NULL, phone = NULL, email = NULL WHERE {clause}"
                ),
                params,
            )
            inv_res = await session.execute(
                text(
                    f"UPDATE invoices SET name = NULL, phone = NULL, email = NULL WHERE {clause}"
                ),
                params,
            )
            cust_count = cust_res.rowcount or 0
            inv_count = inv_res.rowcount or 0
            await session.commit()
    return ok({"customers": cust_count, "invoices": inv_count, "dry_run": payload.dry_run})


__all__ = ["router"]

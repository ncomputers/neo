from __future__ import annotations

"""Privacy DSAR endpoints for data principals."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .db import SessionLocal
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


@router.post("/privacy/dsar/export")
@audit("dsar_export", {"phone", "email"})
async def dsar_export(payload: DSARRequest) -> dict:
    clause, params = payload.filters()
    with SessionLocal() as session:
        cust_rows = session.execute(
            text(
                f"SELECT id, name, phone, email, created_at, allow_analytics, allow_wa FROM customers WHERE {clause}"
            ),
            params,
        ).mappings().all()
        inv_rows = session.execute(
            text(
                f"SELECT id, name, phone, email, created_at FROM invoices WHERE {clause}"
            ),
            params,
        ).mappings().all()
        pay_rows = session.execute(
            text(
                "SELECT p.id, p.invoice_id, p.mode, p.amount, NULL as utr, p.verified, p.created_at "
                "FROM payments p JOIN invoices i ON p.invoice_id = i.id WHERE " + clause
            ),
            params,
        ).mappings().all()
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
    clause, params = payload.filters()
    with SessionLocal() as session:
        if payload.dry_run:
            cust_count = session.execute(
                text(f"SELECT COUNT(*) FROM customers WHERE {clause}"), params
            ).scalar()
            inv_count = session.execute(
                text(f"SELECT COUNT(*) FROM invoices WHERE {clause}"), params
            ).scalar()
            pay_count = session.execute(
                text(
                    "SELECT COUNT(*) FROM payments p JOIN invoices i ON p.invoice_id = i.id WHERE "
                    + clause
                ),
                params,
            ).scalar()
        else:
            pay_res = session.execute(
                text(
                    "UPDATE payments SET utr = NULL WHERE invoice_id IN (SELECT id FROM invoices WHERE "
                    + clause
                    + ")"
                ),
                params,
            )
            inv_res = session.execute(
                text(
                    f"UPDATE invoices SET name = NULL, phone = NULL, email = NULL WHERE {clause}"
                ),
                params,
            )
            cust_res = session.execute(
                text(
                    f"UPDATE customers SET name = NULL, phone = NULL, email = NULL, allow_analytics = 0, allow_wa = 0 WHERE {clause}"
                ),
                params,
            )
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

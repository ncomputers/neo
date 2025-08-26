from __future__ import annotations

"""L1 support console routes for operations staff."""

from fastapi import APIRouter, Depends
from sqlalchemy import select

from .auth import User, role_required
from .db import SessionLocal
from .models_master import Tenant
from .models_tenant import Order, Staff, Table
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


@router.get("/admin/support/console/search")
@audit("support.console.search")
async def search(
    tenant: str | None = None,
    table: str | None = None,
    order: int | None = None,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Lookup tenant, table, or order details.

    Parameters
    ----------
    tenant:
        Tenant identifier to fetch basic metadata.
    table:
        Table code to locate the table within the tenant.
    order:
        Order identifier to fetch order status.
    """

    result: dict = {}
    with SessionLocal() as session:
        if tenant:
            t = session.get(Tenant, tenant)
            if t:
                result["tenant"] = {"id": str(t.id), "name": t.name}
        if table:
            tbl = (
                session.execute(select(Table).where(Table.code == table))
                .scalars()
                .first()
            )
            if tbl:
                result["table"] = {"id": str(tbl.id), "code": tbl.code}
        if order:
            ord_row = session.get(Order, order)
            if ord_row:
                status = getattr(ord_row.status, "name", str(ord_row.status))
                result["order"] = {"id": ord_row.id, "status": status}
    return ok(result)


@router.post("/admin/support/console/order/{order_id}/resend_invoice")
@audit("support.console.resend_invoice")
async def resend_invoice(
    order_id: int,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Trigger invoice resend for ``order_id``."""
    return ok({"order_id": order_id})


@router.post("/admin/support/console/order/{order_id}/reprint_kot")
@audit("support.console.reprint_kot")
async def reprint_kot(
    order_id: int,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Reprint a KOT for ``order_id``."""
    return ok({"order_id": order_id})


@router.post("/admin/support/console/order/{order_id}/replay_webhook")
@audit("support.console.replay_webhook")
async def replay_webhook(
    order_id: int,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Replay webhook events for ``order_id``."""
    return ok({"order_id": order_id})


@router.post("/admin/support/console/staff/{staff_id}/unlock_pin")
@audit("support.console.unlock_pin")
async def unlock_pin(
    staff_id: int,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Unlock a staff member's PIN."""
    with SessionLocal() as session:
        staff = session.get(Staff, staff_id)
        if staff:
            staff.pin_hash = ""
            session.commit()
    return ok({"staff_id": staff_id})

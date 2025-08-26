"""Guest billing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings

from .repos_sqlalchemy import invoices_repo_sql
from .services import billing_service, notifications
from .utils.responses import ok


async def get_tenant_id() -> str:  # pragma: no cover - placeholder dependency
    """Resolve and return the current tenant identifier.

    This stub is a placeholder until multi-tenant plumbing is wired up.
    """
    raise NotImplementedError


async def get_tenant_session(
    tenant_id: str,
) -> AsyncSession:  # pragma: no cover - placeholder
    """Yield an ``AsyncSession`` bound to the tenant database.

    Parameters
    ----------
    tenant_id:
        Identifier of the tenant obtained from :func:`get_tenant_id`.
    """
    raise NotImplementedError


router = APIRouter()


@router.post("/g/{table_token}/bill")
async def generate_bill(
    table_token: str,
    payload: dict | None = None,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Generate an invoice for a dining session.

    This endpoint currently acts as a stub; the database wiring to resolve
    ``table_token`` and persist invoices will be added later. ``payload`` may
    include an optional ``tip`` amount which is added after tax.
    """
    tip = float(payload.get("tip", 0)) if payload else 0
    coupons = payload.get("coupons") if payload else None

    await invoices_repo_sql.generate_invoice(
        session=session,
        order_group_id=0,
        gst_mode="unreg",
        rounding="nearest_1",
        tenant_id=tenant_id,
        tip=tip,
        coupons=coupons,
    )
    settings = get_settings()
    invoice_payload = billing_service.compute_bill(
        [],
        "unreg",
        tip=tip,
        coupons=coupons,
        happy_hour_windows=settings.happy_hour_windows,
    )
    await notifications.enqueue(
        tenant_id, "bill.generated", {"table_token": table_token}
    )
    return ok(invoice_payload)

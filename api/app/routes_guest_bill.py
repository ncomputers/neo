from __future__ import annotations

"""Guest billing routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .repos_sqlalchemy import invoices_repo_sql
from .services import billing_service
from .utils.responses import ok


async def get_tenant_id() -> str:  # pragma: no cover - placeholder dependency
    """Resolve and return the current tenant identifier.

    This stub is a placeholder until multi-tenant plumbing is wired up.
    """
    raise NotImplementedError


async def get_tenant_session(tenant_id: str) -> AsyncSession:  # pragma: no cover - placeholder
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
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Generate an invoice for a dining session.

    This endpoint currently acts as a stub; the database wiring to resolve
    ``table_token`` and persist invoices will be added later.
    """
    await invoices_repo_sql.generate_invoice(
        session=session,
        order_group_id=0,
        gst_mode="unreg",
        rounding="nearest_1",
    )
    invoice_payload = billing_service.compute_bill([], "unreg")
    return ok(invoice_payload)

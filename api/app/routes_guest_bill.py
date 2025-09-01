"""Guest billing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from config import get_settings

from .exp.ab_allocator import get_variant
from .repos_sqlalchemy import invoices_repo_sql
from .routes_metrics import record_ab_conversion
from .services import billing_service, notifications
from .services.receipt_vault import ReceiptVault
from .utils.responses import ok
from .db import SessionLocal
from .db.tenant import get_engine
from .models_tenant import Table


async def get_tenant_id(table_token: str) -> str:
    """Resolve and return the tenant identifier for ``table_token``.

    ``table_token`` is the QR token assigned to a table. The lookup is
    performed synchronously against ``SessionLocal``. If the token is unknown a
    ``404`` is raised.
    """
    with SessionLocal() as session:
        result = session.execute(
            select(Table.tenant_id).where(Table.qr_token == table_token)
        )
        tenant_id = result.scalar_one_or_none()
    if tenant_id is None:
        raise HTTPException(status_code=404, detail="table not found")
    return str(tenant_id)


async def get_tenant_session(
    tenant_id: str,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`~sqlalchemy.ext.asyncio.AsyncSession` for ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with sessionmaker() as session:
        yield session


router = APIRouter()


@router.post("/g/{table_token}/bill")
async def generate_bill(
    table_token: str,
    request: Request,
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
    guest_id = payload.get("guest_id") if payload else None
    outlet_id = payload.get("outlet_id") if payload else None

    await invoices_repo_sql.generate_invoice(
        session=session,
        order_group_id=0,
        gst_mode="unreg",
        rounding="nearest_1",
        tenant_id=tenant_id,
        tip=tip,
        coupons=coupons,
        guest_id=guest_id,
        outlet_id=outlet_id,
        bill_lang=getattr(request.state, "lang", None),
    )
    settings = get_settings()
    invoice_payload = billing_service.compute_bill(
        [],
        "unreg",
        tip=tip,
        coupons=coupons,
        happy_hour_windows=settings.happy_hour_windows,
    )
    contact = None
    if payload:
        contact = payload.get("phone") or payload.get("email")
    if contact and payload and payload.get("consent") and request is not None:
        vault = ReceiptVault(request.app.state.redis)
        await vault.add(contact, invoice_payload)
    device_id = request.headers.get("device-id", "")
    variant = get_variant(device_id, "MENU_COPY_V1")
    record_ab_conversion("MENU_COPY_V1", variant)
    await notifications.enqueue(
        tenant_id, "bill.generated", {"table_token": table_token}
    )
    return ok(invoice_payload)

"""Optional Razorpay/Stripe checkout routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .db.master import get_session
from .models_master import Tenant
from .models_tenant import Payment
from .utils.responses import ok

router = APIRouter()


class CheckoutStart(BaseModel):
    invoice_id: int
    amount: float
    provider: str = "razorpay"


class WebhookPayload(BaseModel):
    order_id: str
    invoice_id: int
    amount: float
    signature: str | None = None


async def get_tenant_session(
    tenant: str,
) -> AsyncSession:  # pragma: no cover - placeholder
    """Yield an ``AsyncSession`` for ``tenant``."""
    raise NotImplementedError


def _gateway_enabled() -> bool:
    return os.getenv("ENABLE_GATEWAY", "false").lower() == "true"


@router.post("/api/outlet/{tenant}/checkout/start")
async def checkout_start(tenant: str, payload: CheckoutStart) -> dict:
    if not _gateway_enabled():
        raise HTTPException(status_code=404)
    async with get_session() as session:
        tenant_row = await session.get(Tenant, tenant)
    if not tenant_row or not getattr(tenant_row, "enable_gateway", False):
        raise HTTPException(status_code=404)
    order_id = f"{payload.provider}_{payload.invoice_id}"
    pay_url = f"https://pay.example/{order_id}"
    return ok({"order_id": order_id, "pay_url": pay_url})


@router.post("/api/outlet/{tenant}/checkout/webhook")
async def checkout_webhook(
    tenant: str,
    payload: WebhookPayload,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    if not _gateway_enabled():
        raise HTTPException(status_code=404)
    async with get_session() as m_session:
        tenant_row = await m_session.get(Tenant, tenant)
    if not tenant_row or not getattr(tenant_row, "enable_gateway", False):
        raise HTTPException(status_code=404)
    payment = Payment(
        invoice_id=payload.invoice_id,
        mode="gateway",
        amount=payload.amount,
        utr=payload.order_id,
        verified=True,
    )
    session.add(payment)
    await session.commit()
    return ok({"attached": True})


__all__ = ["router", "get_tenant_session"]

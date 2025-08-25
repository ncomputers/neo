"""Optional Razorpay/Stripe checkout routes."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .db.master import get_session
from .models_master import Tenant
from .models_tenant import Invoice, Payment
from .utils.responses import ok

router = APIRouter()


class CheckoutStart(BaseModel):
    invoice_id: int
    amount: float


class WebhookPayload(BaseModel):
    order_id: str
    invoice_id: int
    amount: float
    status: str = "paid"
    signature: str | None = None


async def get_tenant_session(
    tenant: str,
) -> AsyncSession:  # pragma: no cover - placeholder
    """Yield an ``AsyncSession`` for ``tenant``."""
    raise NotImplementedError


def _gateway_enabled() -> bool:
    return os.getenv("ENABLE_GATEWAY", "false").lower() == "true"


def _sandbox_enabled(tenant: Tenant | None) -> bool:
    env_flag = os.getenv("GATEWAY_SANDBOX", "false").lower() == "true"
    tenant_flag = bool(getattr(tenant, "gateway_sandbox", False))
    return env_flag or tenant_flag


@router.post("/api/outlet/{tenant}/checkout/start")
async def checkout_start(tenant: str, payload: CheckoutStart) -> dict:
    if not _gateway_enabled():
        raise HTTPException(status_code=404)
    async with get_session() as session:
        tenant_row = await session.get(Tenant, tenant)
    provider = getattr(tenant_row, "gateway_provider", "none") if tenant_row else "none"
    if provider in (None, "none"):
        raise HTTPException(status_code=404)
    sandbox = _sandbox_enabled(tenant_row)
    order_id = f"{provider}_{payload.invoice_id}"
    host = "sandbox-pay.example" if sandbox else "pay.example"
    pay_url = f"https://{host}/{order_id}"
    return ok({"order_id": order_id, "pay_url": pay_url})


@router.post("/api/outlet/{tenant}/checkout/webhook")
async def checkout_webhook(
    tenant: str,
    payload: WebhookPayload,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    if not _gateway_enabled() or not payload.signature:
        raise HTTPException(status_code=404)
    async with get_session() as m_session:
        tenant_row = await m_session.get(Tenant, tenant)
    provider = getattr(tenant_row, "gateway_provider", "none") if tenant_row else "none"
    if provider in (None, "none"):
        raise HTTPException(status_code=404)
    sandbox = _sandbox_enabled(tenant_row)
    secret_env = {
        "razorpay": "RAZORPAY_SECRET_TEST" if sandbox else "RAZORPAY_SECRET",
        "stripe": "STRIPE_SECRET_TEST" if sandbox else "STRIPE_SECRET",
    }
    secret = os.getenv(secret_env.get(provider, ""), "")
    body = f"{payload.order_id}|{payload.invoice_id}|{payload.amount}|{payload.status}"
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.signature):
        raise HTTPException(status_code=400, detail="invalid signature")
    invoice = await session.get(Invoice, payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404)
    if payload.status == "paid":
        if getattr(invoice, "settled", False):
            return ok({"attached": False})
        payment = Payment(
            invoice_id=payload.invoice_id,
            mode="gateway",
            amount=payload.amount,
            utr=payload.order_id,
            verified=True,
        )
        session.add(payment)
        invoice.settled = True
        invoice.settled_at = datetime.now(timezone.utc)
        await session.commit()
        return ok({"attached": True})
    if payload.status == "refund":
        if not getattr(invoice, "settled", False):
            return ok({"refunded": False})
        payment = Payment(
            invoice_id=payload.invoice_id,
            mode="gateway_refund",
            amount=-payload.amount,
            utr=payload.order_id,
            verified=True,
        )
        session.add(payment)
        invoice.settled = False
        invoice.settled_at = None
        await session.commit()
        return ok({"refunded": True})
    raise HTTPException(status_code=400, detail="unknown status")


__all__ = ["router", "get_tenant_session"]

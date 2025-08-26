from __future__ import annotations

import hashlib
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import SessionLocal
from .db.tenant import get_engine
from .deps.tenant import get_tenant_id
from .models_tenant import AuditTenant, Invoice, Payment
from .utils.responses import ok

router = APIRouter()


async def get_tenant_session(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` bound to the tenant database."""

    engine = get_engine(tenant_id)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:  # pragma: no cover - simple generator
        yield session


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Issue a refund for ``payment_id`` and cache the result for 24h."""

    key = request.headers.get("Idempotency-Key")
    if not key:
        raise HTTPException(status_code=400, detail="missing idempotency key")

    redis = request.app.state.redis
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    cache_key = f"refund:{payment_id}:{key_hash}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")

    invoice = await session.get(Invoice, payment.invoice_id)
    if invoice is None or not getattr(invoice, "settled", False):
        result = ok({"refunded": False})
    else:
        refund = Payment(
            invoice_id=payment.invoice_id,
            mode=f"{payment.mode}_refund",
            amount=-payment.amount,
            verified=True,
        )
        session.add(refund)
        invoice.settled = False
        invoice.settled_at = None
        await session.commit()
        result = ok({"refunded": True})

    await redis.set(cache_key, json.dumps(result), ex=86400)
    with SessionLocal() as db:
        db.add(
            AuditTenant(
                actor="system",
                action="payment.refund",
                meta={"payment_id": payment_id, "idempotency_key": key},
            )
        )
        db.commit()

    return result


__all__ = ["router", "get_tenant_session"]

"""Billing routes."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException

from .utils.responses import ok
from .middlewares.license_gate import billing_always_allowed

router = APIRouter()


@router.get("/billing")
@billing_always_allowed
async def billing_info(x_tenant_id: str = Header(...)) -> dict:
    """Return subscription details and payment link for the tenant."""
    from .main import TENANTS  # inline import to avoid circular deps

    tenant = TENANTS.get(x_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan = tenant.get("plan")
    next_renewal = tenant.get("subscription_expires_at")
    pay_url = os.getenv("LICENSE_PAY_URL", "")
    grace_days = tenant.get("grace_period_days", 7)
    now = datetime.utcnow()
    grace = False
    if next_renewal:
        grace = next_renewal < now <= next_renewal + timedelta(days=grace_days)
    return ok(
        {
            "plan": plan,
            "next_renewal": next_renewal,
            "pay_url": pay_url,
            "grace": grace,
        }
    )

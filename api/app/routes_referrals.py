"""Referral signup and credit award routes."""

from __future__ import annotations

import os
from typing import Dict, Set

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .routes_onboarding import TENANTS
from .security import ratelimit
from .utils import ratelimits
from .utils.rate_limit import rate_limited
from .utils.responses import ok

router = APIRouter()

# Environment configuration
REFERRAL_MAX_CREDITS = int(os.getenv("REFERRAL_MAX_CREDITS", "5000"))

# In-memory stores for demo purposes
REFERRAL_CREDITS: Dict[str, int] = {}
SUBSCRIPTION_EVENTS: Set[str] = set()


class SignupPayload(BaseModel):
    """Incoming referral signup attribution payload."""

    referrer_tenant_id: str
    email: str
    phone: str | None = None


@router.post("/referrals/signup")
async def referral_signup(payload: SignupPayload, request: Request):
    """Attribution endpoint for referred signups.

    Applies IP based rate limits and blocks self referrals using owner
    email/phone metadata looked up from :mod:`routes_onboarding` ``TENANTS``.
    """

    ip = request.client.host if request.client else "unknown"
    policy = ratelimits.referral_signup()
    allowed = await ratelimit.allow(
        request.app.state.redis,
        ip,
        "referral_signup",
        rate_per_min=policy.rate_per_min,
        burst=policy.burst,
    )
    if not allowed:
        retry_after = await request.app.state.redis.ttl(
            f"ratelimit:{ip}:referral_signup"
        )
        return rate_limited(retry_after)

    referrer = TENANTS.get(payload.referrer_tenant_id)
    if referrer:
        owner = referrer.get("owner", {})
        if payload.email == owner.get("email") or (
            payload.phone and payload.phone == owner.get("phone")
        ):
            raise HTTPException(status_code=400, detail="self-referral")

    return ok(True)


class CreditPayload(BaseModel):
    """Payload for awarding referral credits."""

    event_id: str
    referrer_tenant_id: str
    amount_inr: int
    invoice_amount_inr: int
    plan_price_inr: int


@router.post("/referrals/credit")
async def referral_credit(payload: CreditPayload):
    """Award referral credit if eligibility checks pass.

    Ensures idempotency using ``subscription_events`` and caps credits per
    referrer based on ``REFERRAL_MAX_CREDITS``.
    """

    if payload.event_id in SUBSCRIPTION_EVENTS:
        return ok({"awarded": 0})
    SUBSCRIPTION_EVENTS.add(payload.event_id)

    if payload.invoice_amount_inr < payload.plan_price_inr:
        return ok({"awarded": 0})

    current = REFERRAL_CREDITS.get(payload.referrer_tenant_id, 0)
    remaining = REFERRAL_MAX_CREDITS - current
    if remaining <= 0:
        return ok({"awarded": 0})

    credit = min(payload.amount_inr, remaining)
    REFERRAL_CREDITS[payload.referrer_tenant_id] = current + credit
    return ok({"awarded": credit})


__all__ = [
    "router",
    "REFERRAL_MAX_CREDITS",
    "REFERRAL_CREDITS",
    "SUBSCRIPTION_EVENTS",
]

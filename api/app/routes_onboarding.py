"""Simple in-memory onboarding wizard endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .utils.responses import ok

router = APIRouter()

# In-memory stores for onboarding sessions and tenants
ONBOARDING_SESSIONS: dict[str, dict] = {}
TENANTS: dict[str, dict] = {}


class Profile(BaseModel):
    """Basic tenant profile information."""

    name: str
    address: str
    logo_url: str | None = None
    timezone: str
    language: str


class Tax(BaseModel):
    """Tax configuration for the tenant."""

    mode: Literal["regular", "composition", "unregistered"]
    gstin: str | None = None
    hsn_required: bool | None = None


class Tables(BaseModel):
    """Table allocation payload."""

    count: int
    codes: list[str] | None = None


class PaymentModes(BaseModel):
    """Accepted payment modes."""

    cash: bool = True
    upi: bool = True
    card: bool = False


class Payments(BaseModel):
    """Payment configuration for the tenant."""

    vpa: str | None = None
    central_vpa: bool | None = None
    modes: PaymentModes


def _session(onboarding_id: str) -> dict:
    session = ONBOARDING_SESSIONS.get(onboarding_id)
    if not session:
        raise HTTPException(404, "Invalid onboarding session")
    return session


@router.post("/api/onboarding/start")
async def start_onboarding() -> dict:
    """Create an onboarding session and return its identifier."""

    onboarding_id = uuid.uuid4().hex
    ONBOARDING_SESSIONS[onboarding_id] = {"id": onboarding_id}
    return ok({"onboarding_id": onboarding_id})


@router.post("/api/onboarding/{onboarding_id}/profile")
async def set_profile(onboarding_id: str, profile: Profile) -> dict:
    session = _session(onboarding_id)
    session["profile"] = profile.model_dump()
    return ok(True)


@router.post("/api/onboarding/{onboarding_id}/tax")
async def set_tax(onboarding_id: str, tax: Tax) -> dict:
    session = _session(onboarding_id)
    session["tax"] = tax.model_dump()
    return ok(True)


@router.post("/api/onboarding/{onboarding_id}/tables")
async def set_tables(onboarding_id: str, tables: Tables) -> dict:
    session = _session(onboarding_id)
    codes = tables.codes or [f"T{i+1}" for i in range(tables.count)]
    allocated = []
    for idx, code in enumerate(codes[: tables.count]):
        allocated.append(
            {
                "code": code,
                "label": f"Table {idx + 1}",
                "qr_token": uuid.uuid4().hex,
            }
        )
    session["tables"] = allocated
    return ok(allocated)


@router.post("/api/onboarding/{onboarding_id}/payments")
async def set_payments(onboarding_id: str, payments: Payments) -> dict:
    session = _session(onboarding_id)
    session["payments"] = payments.model_dump()
    return ok(True)


@router.post("/api/onboarding/{onboarding_id}/finish")
async def finish_onboarding(onboarding_id: str) -> dict:
    session = _session(onboarding_id)
    TENANTS[onboarding_id] = session
    ONBOARDING_SESSIONS.pop(onboarding_id, None)
    return ok({"tenant_id": onboarding_id})


__all__ = ["router", "TENANTS"]

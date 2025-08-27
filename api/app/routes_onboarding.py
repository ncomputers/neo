"""Simple in-memory onboarding wizard endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from .onboarding_store import delete_session, load_session, save_session
from .utils.responses import ok

router = APIRouter()

# Persistent tenants store remains in-memory for demo
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
    """Fetch or create a session for the given onboarding identifier."""
    return load_session(onboarding_id)


@router.post("/api/onboarding/start")
async def start_onboarding() -> dict:
    """Create an onboarding session and return its identifier."""

    onboarding_id = uuid.uuid4().hex
    save_session({"id": onboarding_id, "current_step": "start"})
    return ok({"onboarding_id": onboarding_id})


@router.get("/api/onboarding/{onboarding_id}")
async def get_onboarding(onboarding_id: str) -> dict:
    """Return the stored onboarding session state."""
    session = _session(onboarding_id)
    return ok(session)


@router.post("/api/onboarding/{onboarding_id}/profile")
async def set_profile(onboarding_id: str, profile: Profile) -> dict:
    session = _session(onboarding_id)
    session["profile"] = profile.model_dump()
    session["current_step"] = "profile"
    save_session(session)
    return ok(True)


@router.post("/api/onboarding/{onboarding_id}/tax")
async def set_tax(onboarding_id: str, tax: Tax) -> dict:
    session = _session(onboarding_id)
    session["tax"] = tax.model_dump()
    session["current_step"] = "tax"
    save_session(session)
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
    session["current_step"] = "tables"
    save_session(session)
    return ok(allocated)


@router.post("/api/onboarding/{onboarding_id}/payments")
async def set_payments(onboarding_id: str, payments: Payments) -> dict:
    session = _session(onboarding_id)
    session["payments"] = payments.model_dump()
    session["current_step"] = "payments"
    save_session(session)
    return ok(True)


@router.post("/api/onboarding/{onboarding_id}/finish")
async def finish_onboarding(onboarding_id: str) -> dict:
    session = _session(onboarding_id)
    session["current_step"] = "finished"
    TENANTS[onboarding_id] = session
    delete_session(onboarding_id)
    return ok({"tenant_id": onboarding_id})


__all__ = ["router", "TENANTS"]

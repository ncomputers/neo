from __future__ import annotations

"""Staff login and protected routes using PIN-based auth."""

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .db import SessionLocal
from .models_tenant import Staff
from .staff_auth import StaffToken, create_staff_token, role_required
from .utils.responses import ok

router = APIRouter(prefix="/api/outlet/{tenant}/staff")
ph = PasswordHasher()


class LoginPayload(BaseModel):
    """Credentials for staff PIN login."""

    code: int
    pin: str


@router.post("/login")
async def login(tenant: str, payload: LoginPayload) -> dict:
    """Authenticate a staff member using ``code`` and ``pin``."""

    with SessionLocal() as session:
        staff = session.get(Staff, payload.code)
        if not staff or not staff.active:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        try:
            ph.verify(staff.pin_hash, payload.pin)
        except Exception:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_staff_token(staff.id, staff.role)
    return ok(StaffToken(access_token=token, role=staff.role, staff_id=staff.id))


@router.get("/me")
async def me(staff=Depends(role_required("waiter", "kitchen", "cleaner"))):
    """Return authenticated staff details."""

    return ok({"staff_id": staff.staff_id, "role": staff.role})


__all__ = ["router"]

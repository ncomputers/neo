from __future__ import annotations

"""Staff login and protected routes using PIN-based auth."""

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .audit import log_event
from .db import SessionLocal
from .models_tenant import Staff
from .security.ratelimit import allow
from .staff_auth import StaffToken, create_staff_token, role_required
from .utils.responses import err, ok
from .utils.audit import audit

router = APIRouter(prefix="/api/outlet/{tenant}/staff")
ph = PasswordHasher()


class LoginPayload(BaseModel):
    """Credentials for staff PIN login."""

    code: int
    pin: str


class SetPinPayload(BaseModel):
    """New PIN to assign to a staff member."""

    pin: str


@router.post("/login")
async def login(tenant: str, payload: LoginPayload, request: Request) -> dict:
    """Authenticate a staff member using ``code`` and ``pin``."""

    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    throttle_key = str(payload.code)
    existing = await redis.get(f"ratelimit:{ip}:{throttle_key}")
    if existing and int(existing) >= 5:
        return JSONResponse(
            err("AUTH_THROTTLED", "TooManyRequests"), status_code=403
        )

    with SessionLocal() as session:
        staff = session.get(Staff, payload.code)
        if not staff or not staff.active:
            allowed = await allow(redis, ip, throttle_key, rate_per_min=0.5, burst=5)
            if not allowed:
                return JSONResponse(
                    err("AUTH_THROTTLED", "TooManyRequests"), status_code=403
                )
            raise HTTPException(status_code=400, detail="Invalid credentials")
        try:
            ph.verify(staff.pin_hash, payload.pin)
        except Exception:  # pragma: no cover - defensive
            allowed = await allow(redis, ip, throttle_key, rate_per_min=0.5, burst=5)
            if not allowed:
                return JSONResponse(
                    err("AUTH_THROTTLED", "TooManyRequests"), status_code=403
                )
            raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_staff_token(staff.id, staff.role)
    return ok(StaffToken(access_token=token, role=staff.role, staff_id=staff.id))


@router.post("/{staff_id}/set_pin")
@audit("set_pin")
async def set_pin(
    tenant: str,
    staff_id: int,
    payload: SetPinPayload,
    request: Request,
    staff=Depends(role_required("admin", "manager")),
) -> dict:
    """Set a new PIN for ``staff_id`` and clear login throttling."""

    with SessionLocal() as session:
        target = session.get(Staff, staff_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Staff not found")
        target.pin_hash = ph.hash(payload.pin)
        session.commit()

    redis = request.app.state.redis
    async for key in redis.scan_iter(f"ratelimit:*:{staff_id}"):
        await redis.delete(key)
    log_event(str(staff.staff_id), "set_pin", str(staff_id))
    return ok(True)


@router.get("/me")
async def me(staff=Depends(role_required("waiter", "kitchen", "cleaner"))):
    """Return authenticated staff details."""

    return ok({"staff_id": staff.staff_id, "role": staff.role})


__all__ = ["router"]

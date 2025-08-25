from __future__ import annotations

"""Staff login and protected routes using PIN-based auth."""

from datetime import datetime

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .audit import log_event
from .db import SessionLocal
from .models_tenant import Staff
from .staff_auth import StaffToken, create_staff_token, role_required
from .utils.audit import audit
from .utils.responses import err, ok

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
    fail_key = f"pinfail:{ip}:{payload.code}"
    lock_key = f"pinlock:{ip}:{payload.code}"
    meta_key = f"{lock_key}:meta"

    if await redis.exists(lock_key):
        return JSONResponse(err("AUTH_LOCKED", "TooManyRequests"), status_code=403)
    if await redis.exists(meta_key):
        await redis.delete(meta_key)
        log_event(str(payload.code), "pin_unlock", ip)

    warn = False
    with SessionLocal() as session:
        staff = session.get(Staff, payload.code)
        if not staff or not staff.active:
            fails = await redis.incr(fail_key)
            await redis.expire(fail_key, 900)
            if fails >= 5:
                await redis.set(lock_key, 1, ex=900)
                await redis.set(meta_key, 1, ex=1800)
                log_event(str(payload.code), "pin_lock", ip)
                return JSONResponse(
                    err("AUTH_LOCKED", "TooManyRequests"), status_code=403
                )
            raise HTTPException(status_code=400, detail="Invalid credentials")
        try:
            ph.verify(staff.pin_hash, payload.pin)
        except Exception:  # pragma: no cover - defensive
            fails = await redis.incr(fail_key)
            await redis.expire(fail_key, 900)
            if fails >= 5:
                await redis.set(lock_key, 1, ex=900)
                await redis.set(meta_key, 1, ex=1800)
                log_event(str(payload.code), "pin_lock", ip)
                return JSONResponse(
                    err("AUTH_LOCKED", "TooManyRequests"), status_code=403
                )
            raise HTTPException(status_code=400, detail="Invalid credentials")

        await redis.delete(fail_key)

        age_days = (datetime.utcnow() - staff.pin_set_at).days
        if age_days >= 90:
            raise HTTPException(status_code=403, detail="PIN expired")
        warn = 80 <= age_days < 90

    token = create_staff_token(staff.id, staff.role)
    return ok(
        StaffToken(
            access_token=token,
            role=staff.role,
            staff_id=staff.id,
            rotation_warning=warn or None,
        )
    )


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
        target.pin_set_at = datetime.utcnow()
        session.commit()

    redis = request.app.state.redis
    unlocked = False
    async for key in redis.scan_iter(f"pinlock*:{staff_id}"):
        await redis.delete(key)
        if not unlocked:
            log_event(str(staff.staff_id), "pin_unlock", str(staff_id))
            unlocked = True
    async for key in redis.scan_iter(f"pinfail:*:{staff_id}"):
        await redis.delete(key)
    log_event(str(staff.staff_id), "set_pin", str(staff_id))
    return ok(True)


@router.get("/me")
async def me(staff=Depends(role_required("waiter", "kitchen", "cleaner"))):
    """Return authenticated staff details."""

    return ok({"staff_id": staff.staff_id, "role": staff.role})


__all__ = ["router"]

from __future__ import annotations

"""Staff login and protected routes using PIN-based auth."""

from datetime import datetime, time, timezone
from io import StringIO
import csv
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from argon2 import PasswordHasher
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .audit import log_event
from .db import SessionLocal
from zoneinfo import ZoneInfo
from sqlalchemy import select

from .models_tenant import Staff, AuditTenant
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
    log_event(str(staff.id), "login", tenant)
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


@router.get("/shifts")
async def staff_shifts(tenant: str, date: str, format: str = "json"):
    """Return staff activity summary for ``date``.

    Aggregates logins, KOT accepted, tables cleaned, voids and total time
    logged in for each staff member. Supports CSV via ``format=csv``.
    """

    tz = os.getenv("DEFAULT_TZ", "UTC")
    day = datetime.strptime(date, "%Y-%m-%d").date()
    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    with SessionLocal() as session:
        rows = session.execute(
            select(AuditTenant.actor, AuditTenant.action, AuditTenant.at).where(
                AuditTenant.at >= start, AuditTenant.at <= end
            )
        ).all()

    stats: dict[str, dict[str, Any]] = {}
    for actor, action, at in rows:
        staff_id = actor.split(":")[0]
        if not staff_id.isdigit():
            continue
        entry = stats.setdefault(
            staff_id,
            {
                "logins": 0,
                "kot_accepted": 0,
                "tables_cleaned": 0,
                "voids": 0,
                "_logins": [],
            },
        )
        if action == "login":
            entry["logins"] += 1
            entry["_logins"].append(at)
        elif action == "kot_accept":
            entry["kot_accepted"] += 1
        elif action == "mark_table_ready":
            entry["tables_cleaned"] += 1
        elif action == "void":
            entry["voids"] += 1

    result: list[dict[str, Any]] = []
    for sid, entry in stats.items():
        times = sorted(entry.pop("_logins"))
        total = (
            (times[-1] - times[0]).total_seconds()
            if len(times) >= 2
            else 0.0
        )
        entry["total_time"] = total
        entry["staff_id"] = int(sid)
        result.append(entry)

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "staff_id",
                "logins",
                "kot_accepted",
                "tables_cleaned",
                "voids",
                "total_time",
            ]
        )
        for row in result:
            writer.writerow(
                [
                    row["staff_id"],
                    row["logins"],
                    row["kot_accepted"],
                    row["tables_cleaned"],
                    row["voids"],
                    row["total_time"],
                ]
            )
        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=staff-shifts.csv"
        return response

    return ok(result)


__all__ = ["router"]

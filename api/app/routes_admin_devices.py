from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from .auth import User, role_required
from .db import SessionLocal
from .models_master import Device
from .utils.responses import ok
from .utils.audit import audit
from .audit import log_event

router = APIRouter()


class DevicePayload(BaseModel):
    name: str
    fingerprint: str


@router.post("/admin/devices/register")
@audit("devices.register")
async def register_device(
    payload: DevicePayload,
    user: User = Depends(role_required("super_admin", "manager")),
) -> dict:
    with SessionLocal() as session:
        device = Device(name=payload.name, fingerprint=payload.fingerprint)
        session.add(device)
        session.commit()
        return ok(
            {
                "id": device.id,
                "name": device.name,
                "fingerprint": device.fingerprint,
            }
        )


@router.get("/admin/devices")
@audit("devices.list")
async def list_devices(
    user: User = Depends(role_required("super_admin", "manager")),
) -> dict:
    with SessionLocal() as session:
        items = [
            {"id": d.id, "name": d.name, "fingerprint": d.fingerprint}
            for d in session.query(Device).all()
        ]
    return ok(items)


@router.post("/admin/staff/{username}/unlock_pin")
@audit("staff.unlock_pin")
async def unlock_pin(
    username: str,
    request: Request,
    user: User = Depends(role_required("super_admin", "manager")),
) -> dict:
    redis = request.app.state.redis
    tenant = request.headers.get("X-Tenant-ID", "demo")
    async for key in redis.scan_iter(f"pin:lock:{tenant}:{username}:*"):
        await redis.delete(key)
    async for key in redis.scan_iter(f"pin:lockstatus:{tenant}:{username}:*"):
        await redis.delete(key)
    async for key in redis.scan_iter(f"pin:fail:{tenant}:{username}:*"):
        await redis.delete(key)
    log_event(username, "pin_unlock", tenant)
    return ok(True)


__all__ = ["router"]

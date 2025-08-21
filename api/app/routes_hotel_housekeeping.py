from __future__ import annotations

"""Endpoints for hotel room housekeeping and cleaning workflows."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from .auth import User, role_required
from .db import SessionLocal
from .events import event_bus
from .models_tenant import Room
from .utils.responses import ok


router = APIRouter(prefix="/api/outlet/{tenant}/housekeeping")


@router.post("/room/{room_id}/start_clean")
async def start_clean_room(
    tenant: str,
    room_id: int,
    user: User = Depends(role_required("cleaner", "admin")),
) -> dict:
    """Mark ``room_id`` as awaiting cleaning."""

    with SessionLocal() as session:
        room = session.get(Room, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        room.state = "PENDING_CLEANING"
        session.commit()
        session.refresh(room)
        return ok({"room_id": str(room_id), "state": room.state})


@router.post("/room/{room_id}/ready")
async def mark_room_ready(
    tenant: str,
    room_id: int,
    user: User = Depends(role_required("cleaner", "admin")),
) -> dict:
    """Mark cleaning complete and reopen the room."""

    await event_bus.publish("room.cleaned", {"room_id": room_id})
    with SessionLocal() as session:
        room = session.get(Room, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        room.state = "AVAILABLE"
        room.last_cleaned_at = func.now()
        session.commit()
        session.refresh(room)
        return ok({"room_id": str(room_id), "state": room.state})


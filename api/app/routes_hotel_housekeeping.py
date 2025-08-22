from __future__ import annotations

"""Endpoints for hotel room housekeeping and cleaning workflows."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Generator

from .auth import User, role_required
from .db import SessionLocal
from .deps.tenant import get_tenant_id
from .events import event_bus
from .models_tenant import Room
from .utils.responses import ok
from .utils.audit import audit


router = APIRouter(prefix="/api/outlet/housekeeping")


def get_tenant_session(tenant_id: str = Depends(get_tenant_id)) -> Generator[Session, None, None]:
    """Yield a database session for ``tenant_id``.

    Currently this uses the shared ``SessionLocal`` engine as a placeholder
    until tenant-specific engines are wired.
    """

    with SessionLocal() as session:
        yield session


@router.post("/room/{room_id}/start_clean")
@audit("start_clean_room")
async def start_clean_room(
    room_id: int,
    user: User = Depends(role_required("cleaner", "admin")),
    session: Session = Depends(get_tenant_session),
) -> dict:
    """Mark ``room_id`` as awaiting cleaning."""

    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    room.state = "PENDING_CLEANING"
    session.commit()
    session.refresh(room)
    return ok({"room_id": str(room_id), "state": room.state})


@router.post("/room/{room_id}/ready")
@audit("mark_room_ready")
async def mark_room_ready(
    room_id: int,
    user: User = Depends(role_required("cleaner", "admin")),
    session: Session = Depends(get_tenant_session),
) -> dict:
    """Mark cleaning complete and reopen the room."""

    await event_bus.publish("room.cleaned", {"room_id": room_id})
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    room.state = "AVAILABLE"
    room.last_cleaned_at = func.now()
    session.commit()
    session.refresh(room)
    return ok({"room_id": str(room_id), "state": room.state})

from __future__ import annotations

"""Expose simple aggregate metrics via /api/stats."""

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import func

from .db import SessionLocal
from .models_tenant import Staff

router = APIRouter()

_START_TIME = datetime.utcnow()


@router.get("/api/stats")
async def get_stats() -> dict[str, int]:
    """Return basic uptime and user metrics."""
    uptime = int((datetime.utcnow() - _START_TIME).total_seconds())
    with SessionLocal() as session:
        staff_count = session.execute(func.count(Staff.id)).scalar() or 0
    return {"uptime_s": uptime, "staff_count": staff_count}


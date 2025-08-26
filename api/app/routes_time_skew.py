from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/time/skew")
async def time_skew() -> dict:
    """Return the current server epoch time."""
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    return {"epoch": epoch}

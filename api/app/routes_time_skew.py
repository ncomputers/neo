from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/time/skew")
async def time_skew(
    client_ts: Optional[int] = Query(None, description="Client timestamp in ms")
) -> dict:
    """Return server time and advice for client clock skew."""
    now = datetime.now(timezone.utc)
    server_ms = int(now.timestamp() * 1000)
    resp = {"server_time": now.isoformat()}
    if client_ts is None:
        resp["advice"] = "Provide client_ts to check skew"
    else:
        skew = server_ms - client_ts
        resp["skew_ms"] = skew
        if abs(skew) > 120_000:
            resp["advice"] = "Your device clock is out of sync. Please correct it."
        else:
            resp["advice"] = "Time is in sync."
    return resp

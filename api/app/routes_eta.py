from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from .eta import service
from .utils.responses import ok

router = APIRouter()


@router.get("/orders/{order_id}/eta")
async def order_eta(order_id: int) -> dict:
    """Return ETA information for ``order_id``."""
    result = service.eta_for_order([], active_tickets=1)
    now = datetime.utcnow()
    late_by = max(0, int((now - result["promised_at"]).total_seconds() * 1000))
    data = {
        "eta_ms": result["eta_ms"],
        "promised_at": result["promised_at"],
        "late_by_ms": late_by,
    }
    return ok(data)

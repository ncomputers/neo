"""Routes for collecting guest feedback and providing admin summaries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import User, role_required
from .utils.responses import ok


class FeedbackIn(BaseModel):
    """Incoming feedback payload from a guest."""

    table_code: str = Field(..., description="Table identifier")
    rating: Literal["up", "down"] = Field(..., description="Thumbs up or down")
    note: str | None = Field(default=None, description="Optional free-form note")


class FeedbackRecord(FeedbackIn):
    """Stored feedback entry with timestamp."""

    timestamp: datetime


# In-memory store: tenant -> list[FeedbackRecord]
FEEDBACK_STORE: dict[str, list[FeedbackRecord]] = {}

router = APIRouter()


@router.post("/api/outlet/{tenant}/feedback")
async def submit_feedback(
    tenant: str,
    fb: FeedbackIn,
    user: User = Depends(role_required("guest")),
) -> dict:
    """Accept a feedback submission from a guest."""

    record = FeedbackRecord(**fb.model_dump(), timestamp=datetime.utcnow())
    FEEDBACK_STORE.setdefault(tenant, []).append(record)
    return ok({"received": True})


@router.get("/api/outlet/{tenant}/feedback/summary")
async def feedback_summary(
    tenant: str,
    range: int = 30,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Return aggregated feedback counts within the given day range."""

    cutoff = datetime.utcnow() - timedelta(days=range)
    records = [r for r in FEEDBACK_STORE.get(tenant, []) if r.timestamp >= cutoff]
    up = sum(1 for r in records if r.rating == "up")
    down = sum(1 for r in records if r.rating == "down")
    return ok({"up": up, "down": down})

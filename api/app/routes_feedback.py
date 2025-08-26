"""Routes for collecting Net Promoter Score (NPS) feedback."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import User, role_required
from .services.analytics import track
from .utils.responses import ok


class FeedbackIn(BaseModel):
    """Incoming NPS feedback payload from a guest."""

    score: int = Field(..., ge=0, le=10, description="NPS score 0-10")
    comment: str | None = Field(default=None, description="Optional free-form comment")


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
    """Accept an NPS feedback submission from a guest."""

    record = FeedbackRecord(**fb.model_dump(), timestamp=datetime.utcnow())
    FEEDBACK_STORE.setdefault(tenant, []).append(record)
    await track(tenant, "feedback_submitted", {"score": fb.score})
    return ok({"received": True})


@router.get("/api/outlet/{tenant}/feedback/summary")
async def feedback_summary(
    tenant: str,
    range: int = 30,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Return aggregated NPS metrics within the given day range."""

    cutoff = datetime.utcnow() - timedelta(days=range)
    records = [r for r in FEEDBACK_STORE.get(tenant, []) if r.timestamp >= cutoff]
    total = len(records)
    promoters = sum(1 for r in records if r.score >= 9)
    detractors = sum(1 for r in records if r.score <= 6)
    nps = ((promoters - detractors) / total * 100) if total else 0.0
    return ok(
        {
            "nps": nps,
            "promoters": promoters,
            "detractors": detractors,
            "responses": total,
        }
    )

"""Routes for collecting pilot NPS feedback."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field


class PilotFeedbackIn(BaseModel):
    """Incoming NPS feedback from pilot users."""

    score: int = Field(..., ge=0, le=10, description="0-10 NPS score")
    comment: str | None = Field(default=None, description="Optional free-form comment")
    contact_opt_in: bool = Field(
        default=False, description="Consent for follow-up contact"
    )


class PilotFeedbackRecord(PilotFeedbackIn):
    """Stored pilot feedback entry with timestamp."""

    timestamp: datetime


# In-memory store: tenant -> list[PilotFeedbackRecord]
PILOT_FEEDBACK_STORE: dict[str, list[PilotFeedbackRecord]] = {}

router = APIRouter()


@router.post("/api/pilot/{tenant}/feedback")
async def submit_pilot_feedback(tenant: str, fb: PilotFeedbackIn) -> dict:
    """Accept an NPS feedback submission for ``tenant``."""

    record = PilotFeedbackRecord(**fb.model_dump(), timestamp=datetime.utcnow())
    PILOT_FEEDBACK_STORE.setdefault(tenant, []).append(record)
    return {"received": True}


@router.get("/api/pilot/admin/feedback/summary")
async def pilot_feedback_summary(
    from_: date = Query(..., alias="from"),
    to: date | None = Query(None, alias="to"),
) -> dict:
    """Return aggregated score buckets for the given date range."""

    end = to or from_
    start_dt = datetime.combine(from_, time.min)
    end_dt = datetime.combine(end, time.max)
    records = [
        r
        for recs in PILOT_FEEDBACK_STORE.values()
        for r in recs
        if start_dt <= r.timestamp <= end_dt
    ]
    total = len(records)
    promoters = sum(1 for r in records if r.score >= 9)
    passives = sum(1 for r in records if 7 <= r.score <= 8)
    detractors = sum(1 for r in records if r.score <= 6)
    return {
        "data": {
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "responses": total,
        }
    }

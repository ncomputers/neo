"""Routes for collecting pilot NPS feedback."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter


class PilotFeedbackIn(BaseModel):
    """Incoming NPS feedback from pilot users."""

    score: int = Field(..., ge=0, le=10, description="0-10 NPS score")
    comment: str | None = Field(
        default=None, description="Optional free-form comment"
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

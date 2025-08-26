"""Admin operations endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .auth import User, role_required
from .slo import slo_tracker
from .utils.responses import ok

router = APIRouter()


@router.get("/admin/ops/slo")
async def get_slo(
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Return rolling 30-day error budget per route."""
    return ok(slo_tracker.report())

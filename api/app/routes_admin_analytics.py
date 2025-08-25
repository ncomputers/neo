"""Admin endpoints for owner analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .auth import User, role_required
from .services.owner_analytics import compute_owner_time_series
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/analytics/owners")
async def admin_owner_analytics(
    days: int = 30, user: User = Depends(role_required("super_admin"))
) -> dict:
    """Return owner cohort and retention metrics as a time series."""
    data = await compute_owner_time_series(days)
    return ok(data)

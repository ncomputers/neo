"""Owner analytics admin endpoints."""
from __future__ import annotations

import json
from fastapi import APIRouter, Depends, Request

from .auth import User, role_required
from .services.owner_analytics import compute_owner_time_series
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/analytics/owners")
async def admin_owner_analytics(
    request: Request,
    range: int = 30,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Return owner cohort and retention metrics for the given range.

    Results are cached for 10 minutes to reduce load.
    """
    redis = request.app.state.redis
    cache_key = f"analytics:owners:{range}"
    cached = await redis.get(cache_key)
    if cached:
        return ok(json.loads(cached))

    data = await compute_owner_time_series(range)
    await redis.set(cache_key, json.dumps(data), ex=600)
    return ok(data)

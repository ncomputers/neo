from __future__ import annotations

"""Admin routes for inspecting background job workers."""

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, Request

from .auth import User, role_required
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/jobs/status")
async def jobs_status(
    request: Request,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Return status information for background workers."""

    redis = request.app.state.redis
    now_ts = datetime.now(timezone.utc).timestamp()
    data: Dict[str, Dict[str, object]] = {}
    keys = await redis.keys("jobs:heartbeat:*")
    for key in keys:
        name = key.split(":")[-1]
        last = await redis.get(key)
        if isinstance(last, bytes):
            last = last.decode()
        processed_raw = await redis.get(f"jobs:processed:{name}")
        processed = int(processed_raw or 0)
        failures = int(
            await redis.zcount(
                f"jobs:failures:{name}", now_ts - 3600, "+inf"
            )
        )
        queue_depths: Dict[str, int] = {}
        queues = await redis.smembers(f"jobs:queues:{name}")
        for q in queues:
            qname = q.decode() if isinstance(q, bytes) else q
            queue_depths[qname] = await redis.llen(f"jobs:queue:{qname}")
        data[name] = {
            "last_heartbeat": last,
            "processed_count": processed,
            "failures_1h": failures,
            "queue_depths": queue_depths,
        }
    return ok(data)

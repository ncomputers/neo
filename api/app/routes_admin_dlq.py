from __future__ import annotations

"""Admin routes for dead-letter queue operations."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import User, role_required
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()

_VALID_TYPES = {"webhook", "export"}


@router.get("/api/admin/dlq")
@audit("dlq_list")
async def list_dlq(
    request: Request,
    type: str = Query(...),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    if type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail="INVALID_TYPE")
    redis = request.app.state.redis
    key = f"jobs:dlq:{type}"
    items = await redis.lrange(key, -100, -1)
    rows = [json.loads(item) for item in items]
    return ok(rows)


@router.post("/api/admin/dlq/replay/{item_id}")
@audit("dlq_replay")
async def replay_dlq(
    item_id: str,
    request: Request,
    type: str = Query(...),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    if type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail="INVALID_TYPE")
    redis = request.app.state.redis
    key = f"jobs:dlq:{type}"
    queue_key = f"jobs:queue:{type}"
    entries = await redis.lrange(key, 0, -1)
    target_raw = None
    target_data: dict | None = None
    for raw in entries:
        data = json.loads(raw)
        if str(data.get("id")) == item_id:
            target_raw = raw
            target_data = data
            break
    if target_raw and target_data is not None:
        await redis.lrem(key, 0, target_raw)
        await redis.rpush(queue_key, json.dumps(target_data))
    return ok({})


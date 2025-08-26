"""Admin routes for dead-letter queue operations."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from .auth import User, role_required
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()

_VALID_TYPES = {"webhook", "export"}
_MAX_ITEMS = 100


class ReplayRequest(BaseModel):
    id: str


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
    items = await redis.lrange(key, -_MAX_ITEMS, -1)
    rows = []
    for item in items:
        data = json.loads(item)
        rows.append(
            {
                "id": data.get("id"),
                "type": data.get("type"),
                "created_at": data.get("created_at"),
                "reason": data.get("reason"),
                "last_error": data.get("last_error"),
            }
        )
    return ok(rows)


@router.post("/api/admin/dlq/replay")
@audit("dlq_replay")
async def replay_dlq(
    payload: ReplayRequest,
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
    target_data = None
    for raw in entries:
        data = json.loads(raw)
        if str(data.get("id")) == payload.id:
            target_raw = raw
            target_data = data
            break
    if target_raw and target_data is not None:
        await redis.lrem(key, 0, target_raw)
        await redis.rpush(queue_key, json.dumps(target_data))
    return ok({})

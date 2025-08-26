from __future__ import annotations

"""Admin routes to inspect and replay dead-lettered jobs."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .audit import log_event
from .auth import User, role_required
from .utils.responses import err, ok

router = APIRouter()


@router.get("/api/admin/dlq")
async def list_dlq(
    type: Literal["webhook", "export"],
    request: Request,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """List recent dead-lettered jobs for the given type."""

    redis = request.app.state.redis
    key = f"jobs:dlq:{type}"
    items = await redis.lrange(key, -50, -1)
    rows = []
    for raw in reversed(items):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        rows.append(
            {
                "id": data.get("id"),
                "reason": data.get("reason"),
                "last_error": data.get("last_error"),
            }
        )
    return ok(rows)


class ReplayPayload(BaseModel):
    id: str
    type: Literal["webhook", "export"]


@router.post("/api/admin/dlq/replay")
async def replay_dlq(
    payload: ReplayPayload,
    request: Request,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Re-enqueue a dead-lettered job."""

    redis = request.app.state.redis
    dlq_key = f"jobs:dlq:{payload.type}"
    queue_key = f"jobs:queue:{payload.type}"
    items = await redis.lrange(dlq_key, 0, -1)
    target = None
    for item in items:
        try:
            data = json.loads(item)
        except Exception:
            continue
        if data.get("id") == payload.id:
            target = item
            break
    if target is None:
        return JSONResponse(err("NOT_FOUND", "DLQ entry not found"), status_code=404)
    pipe = redis.pipeline()
    pipe.lrem(dlq_key, 0, target)
    pipe.lpush(queue_key, target)
    await pipe.execute()
    log_event(user.username, "dlq_replay", f"{payload.type}:{payload.id}", master=True)
    return ok({"requeued": payload.id})

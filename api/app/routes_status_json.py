from __future__ import annotations

import json
from pathlib import Path
from typing import List, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from .auth import role_required
from .utils.responses import ok

router = APIRouter()

STATUS_KEY = "status_json"
STATUS_FILE = Path(__file__).resolve().parent.parent.parent / "status.json"


class StatusPayload(BaseModel):
    state: Literal["ok", "degraded", "outage"]
    message: str | None = None
    components: List[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


@router.get("/status.json")
async def get_status(request: Request):
    data = None
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis:
        try:
            raw = await redis.get(STATUS_KEY)
            if raw:
                data = json.loads(raw)
        except Exception:
            data = None
    if not data:
        try:
            with STATUS_FILE.open() as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"state": "outage", "message": None, "components": []}
    return JSONResponse(data)


@router.post("/admin/status", dependencies=[Depends(role_required("super_admin"))])
async def set_status(payload: StatusPayload, request: Request):
    data = payload.dict()
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis:
        await redis.set(STATUS_KEY, json.dumps(data))
    with STATUS_FILE.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return ok(data)

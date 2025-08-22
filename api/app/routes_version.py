from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/version")
async def version() -> dict:
    return {
        "app": "neo",
        "sha": os.getenv("GIT_SHA", "unknown"),
        "built_at": os.getenv("BUILT_AT", "unknown"),
    }

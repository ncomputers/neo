from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/pwa/version")
async def pwa_version() -> dict:
    return {
        "build": os.getenv("GIT_SHA", "unknown"),
        "time": os.getenv("BUILT_AT", "unknown"),
    }

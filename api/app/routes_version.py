from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()

VALID_ENVS = {"prod", "staging", "dev"}


@router.get("/version")
async def version() -> dict:
    env = os.getenv("ENV", "dev")
    if env not in VALID_ENVS:
        env = "dev"
    return {
        "sha": os.getenv("GIT_SHA", "unknown"),
        "built_at": os.getenv("BUILT_AT", "unknown"),
        "env": env,
    }


@router.get("/pwa/version")
async def pwa_version() -> dict:
    return {
        "build": os.getenv("GIT_SHA", "unknown"),
        "time": os.getenv("BUILT_AT", "unknown"),
    }

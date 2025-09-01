from __future__ import annotations

"""Readiness probe endpoints."""

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .db import SessionLocal
from .utils.responses import err

router = APIRouter()


@router.get("/ready")
async def ready() -> dict:
    """Return readiness status after verifying DB and Redis connectivity."""

    if os.getenv("DISABLE_DB_READY_CHECK") == "1":
        return {"ok": True}

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        # Import lazily to avoid circular import with main.py
        from .main import redis_client

        if redis_client is not None:
            await redis_client.ping()
    except Exception:  # pragma: no cover - best effort only
        return JSONResponse(err("READY_FAIL", "Readiness check failed"), status_code=503)
    return {"ok": True}

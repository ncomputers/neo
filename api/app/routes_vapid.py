"""Expose the VAPID public key for Web Push."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from config import get_settings

router = APIRouter()


@router.get("/api/vapid/public_key")
async def vapid_public_key() -> dict:
    """Return the configured VAPID public key."""
    key = get_settings().vapid_public_key
    if not key:
        raise HTTPException(status_code=404, detail="VAPID key not configured")
    return {"key": key}

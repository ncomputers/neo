"""Expose VAPID public key for Web Push."""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/vapid/public_key")
async def get_vapid_public_key() -> dict:
    """Return configured VAPID public key."""
    return {"key": os.getenv("VAPID_PUBLIC_KEY", "")}

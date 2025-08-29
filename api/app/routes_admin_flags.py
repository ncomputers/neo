"""Endpoints for runtime feature flag toggles."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from . import flags
from .auth import User, role_required
from .utils.responses import ok


router = APIRouter(prefix="/admin/flags")


@router.get("")
async def list_flags(user: User = Depends(role_required("super_admin"))) -> dict:
    """Return current flag values."""
    data = {name: flags.get(name) for name in flags.REGISTRY}
    return ok(data)


class FlagUpdate(BaseModel):
    value: bool


@router.post("/{name}")
async def set_flag(
    name: str, payload: FlagUpdate, user: User = Depends(role_required("super_admin"))
) -> dict:
    """Set a runtime override for a flag."""
    flags.set_override(name, payload.value)
    return ok({name: flags.get(name)})


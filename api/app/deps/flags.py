from __future__ import annotations

"""Dependency helpers for feature flag enforcement."""

from fastapi import Depends, HTTPException

from .tenant import get_tenant_id
from ..utils.flags import can_use


def require_flag(flag: str):
    """Return a dependency that ensures ``flag`` is enabled for the tenant."""

    async def _checker(tenant_id: str = Depends(get_tenant_id)) -> None:
        if not await can_use(tenant_id, flag):
            raise HTTPException(status_code=404, detail="DISABLED")

    return _checker

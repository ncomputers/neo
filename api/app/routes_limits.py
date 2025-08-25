from __future__ import annotations

"""Endpoint to inspect licensing usage and limits for a tenant."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request

from .auth import User, role_required
from .middlewares import licensing as lic_module
from .utils.responses import ok

router = APIRouter()


@router.get("/api/outlet/{tenant}/limits/usage")
async def licensing_usage(
    tenant: str,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Return current usage and configured limits for ``tenant``."""

    tenant_obj = getattr(request.state, "tenant", None)
    if tenant_obj is None:  # pragma: no cover - defensive
        return ok({})
    tenant_id = str(tenant_obj.id)
    limits = getattr(tenant_obj, "license_limits", {}) or {}
    tables = await lic_module._table_count(tenant_id)
    items = await lic_module._menu_item_count(tenant_id)
    storage = lic_module.storage_bytes(tenant_id)
    redis = getattr(request.app.state, "redis", None)
    today = datetime.utcnow().strftime("%Y%m%d")
    exports = 0
    if redis is not None:
        exports = int(await redis.get(f"usage:{tenant_id}:exports:{today}") or 0)

    def _fmt(limit: int | float | None, used: int | float) -> dict:
        remaining = None if limit is None else max(limit - used, 0)
        return {"limit": limit, "used": used, "remaining": remaining}

    return ok(
        {
            "tables": _fmt(limits.get("max_tables"), tables),
            "menu_items": _fmt(limits.get("max_menu_items"), items),
            "images_mb": _fmt(
                limits.get("max_images_mb"), round(storage / (1024 * 1024), 2)
            ),
            "daily_exports": _fmt(limits.get("max_daily_exports"), exports),
        }
    )


__all__ = ["router"]

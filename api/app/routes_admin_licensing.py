from __future__ import annotations

"""Admin endpoint to inspect licensing usage and limits."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request

from .auth import User, role_required
from .middlewares import licensing as lic_module
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/licensing/usage")
async def licensing_usage(
    request: Request,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Return current usage and configured limits for the tenant."""

    tenant = getattr(request.state, "tenant", None)
    if tenant is None:  # pragma: no cover - defensive
        return ok({})
    tenant_id = str(tenant.id)
    limits = getattr(tenant, "license_limits", {}) or {}
    tables = await lic_module._table_count(tenant_id)
    items = await lic_module._menu_item_count(tenant_id)
    storage = lic_module.storage_bytes(tenant_id)
    redis = getattr(request.app.state, "redis", None)
    today = datetime.utcnow().strftime("%Y%m%d")
    exports = 0
    if redis is not None:
        exports = int(await redis.get(f"usage:{tenant_id}:exports:{today}") or 0)
    return ok(
        {
            "tables": {"used": tables, "limit": limits.get("max_tables")},
            "menu_items": {"used": items, "limit": limits.get("max_menu_items")},
            "image_storage_mb": {
                "used": round(storage / (1024 * 1024), 2),
                "limit": limits.get("max_image_storage_mb"),
            },
            "daily_exports": {
                "used": exports,
                "limit": limits.get("max_daily_exports"),
            },
        }
    )


__all__ = ["router"]

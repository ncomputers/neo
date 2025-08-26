from __future__ import annotations

"""Admin endpoint to bootstrap demo sandbox tenants."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends

from .auth import User, role_required
from .utils.responses import ok

router = APIRouter()

_SANDBOX_TENANTS: Dict[str, Dict] = {}


def _demo_menu() -> Dict:
    """Return a sample menu without any PII."""

    return {
        "items": [
            {"id": uuid.uuid4().hex, "name": "Demo Coffee", "price": 250},
            {"id": uuid.uuid4().hex, "name": "Demo Sandwich", "price": 450},
        ]
    }


def _demo_settings() -> Dict:
    """Return placeholder tenant settings."""

    return {"currency": "USD"}


def _demo_orders() -> List[Dict]:
    """Seed demo orders for the sandbox tenant."""

    return [
        {"id": uuid.uuid4().hex, "status": "paid", "total": 700},
        {"id": uuid.uuid4().hex, "status": "pending", "total": 250},
    ]


def _purge_expired(now: datetime) -> None:
    for key, info in list(_SANDBOX_TENANTS.items()):
        if info["expires_at"] <= now:
            _SANDBOX_TENANTS.pop(key, None)


@router.post("/api/admin/tenant/sandbox")
async def create_sandbox_tenant(user: User = Depends(role_required("super_admin"))) -> dict:
    """Create a temporary sandbox tenant with demo data.

    The sandbox copies menu/settings without personal information,
    seeds a couple of demo orders and expires automatically in 7 days.
    """

    now = datetime.utcnow()
    _purge_expired(now)

    sandbox_id = uuid.uuid4().hex
    expires_at = now + timedelta(days=7)

    tenant_data = {
        "menu": _demo_menu(),
        "settings": _demo_settings(),
        "orders": _demo_orders(),
        "expires_at": expires_at,
    }

    _SANDBOX_TENANTS[sandbox_id] = tenant_data

    return ok({"tenant_id": sandbox_id, "expires_at": expires_at.isoformat()})


__all__ = ["router", "_SANDBOX_TENANTS"]

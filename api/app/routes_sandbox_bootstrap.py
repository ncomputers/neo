"""Admin endpoint to bootstrap demo sandbox tenants without PII."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends

from .auth import User, role_required
from .audit import log_event
from .utils.responses import ok

router = APIRouter()

# in-memory store of sandbox tenants created for demos
_SANDBOX_TENANTS: Dict[str, Dict] = {}


def _clone_menu() -> Dict:
    """Return a minimal demo menu with identifiers but no personal data."""

    return {
        "items": [
            {"id": uuid.uuid4().hex, "name": "Demo Coffee", "price": 250},
            {"id": uuid.uuid4().hex, "name": "Demo Sandwich", "price": 450},
        ]
    }


def _clone_settings() -> Dict:
    """Return placeholder tenant settings stripped of PII."""

    return {"currency": "USD"}


def _seed_demo_orders() -> List[Dict]:
    """Seed a couple of demo orders for the sandbox tenant."""

    return [
        {"id": uuid.uuid4().hex, "status": "paid", "total": 700},
        {"id": uuid.uuid4().hex, "status": "pending", "total": 250},
    ]


def _purge_expired(now: datetime) -> None:
    """Remove sandbox tenants whose expiration time has passed."""

    for key, info in list(_SANDBOX_TENANTS.items()):
        if info["expires_at"] <= now:
            _SANDBOX_TENANTS.pop(key, None)


@router.post("/admin/tenant/sandbox")
async def bootstrap_sandbox(
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Create a temporary sandbox tenant with demo data.

    The sandbox copies menu/settings without personal information, seeds demo
    orders and expires automatically in 7 days. An audit entry records the newly
    created sandbox tenant identifier.
    """

    now = datetime.utcnow()
    _purge_expired(now)

    sandbox_id = uuid.uuid4().hex
    expires_at = now + timedelta(days=7)
    tenant_data = {
        "menu": _clone_menu(),
        "settings": _clone_settings(),
        "orders": _seed_demo_orders(),
        "expires_at": expires_at,
    }
    _SANDBOX_TENANTS[sandbox_id] = tenant_data

    # persist audit log with the sandbox tenant id
    log_event(user.username, "sandbox.create", sandbox_id)

    return ok({"tenant_id": sandbox_id, "expires_at": expires_at.isoformat()})


__all__ = ["router", "_SANDBOX_TENANTS", "_purge_expired"]

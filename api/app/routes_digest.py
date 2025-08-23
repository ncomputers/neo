from __future__ import annotations

"""API route to trigger the daily KPI digest."""

from fastapi import APIRouter, Depends

from .auth import User, role_required
from scripts import daily_digest

router = APIRouter()


@router.post("/api/outlet/{tenant_id}/digest/run")
async def run_digest(
    tenant_id: str,
    date: str | None = None,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Send the KPI digest for ``tenant_id`` on ``date``."""

    providers = tuple(daily_digest.PROVIDERS.keys())
    await daily_digest.main(tenant_id, date, providers=providers)
    return {"sent": True, "channels": list(providers)}

from __future__ import annotations

"""Route to trigger daily KPI digest via API."""

import importlib.util
from pathlib import Path
from typing import Sequence

from fastapi import APIRouter, Depends

from .auth import User, role_required

router = APIRouter()

# Load the CLI script as a module so we can reuse its ``main`` function
_spec = importlib.util.spec_from_file_location(
    "daily_digest", Path(__file__).resolve().parents[2] / "scripts" / "daily_digest.py"
)
_daily_digest = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_daily_digest)  # type: ignore


@router.post("/api/outlet/{tenant}/digest/run")
async def run_digest(
    tenant: str,
    date: str | None = None,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    """Compute and send the daily KPI digest for ``tenant``.

    Returns the list of channels the digest was sent to.
    """

    channels: Sequence[str] = ("console", "whatsapp")
    await _daily_digest.main(tenant, date, channels)
    return {"sent": True, "channels": list(channels)}

from __future__ import annotations

"""Superadmin routes for provisioning outlets."""

from pathlib import Path
from uuid import uuid4
import subprocess
import sys

from fastapi import APIRouter
from pydantic import BaseModel

from utils.responses import ok


router = APIRouter(prefix="/api/super")


class OutletPayload(BaseModel):
    """Payload for creating a new outlet."""

    name: str
    domain: str | None = None
    tz: str | None = None
    plan_tables: int | None = None


@router.post("/outlet")
def create_outlet(payload: OutletPayload) -> dict:
    """Provision a new tenant and initialise its database."""

    tenant_id = str(uuid4())
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    subprocess.run(
        [sys.executable, str(scripts_dir / "tenant_create_db.py"), "--tenant", tenant_id],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(scripts_dir / "tenant_migrate.py"), "--tenant", tenant_id],
        check=True,
    )
    return ok({"tenant_id": tenant_id})

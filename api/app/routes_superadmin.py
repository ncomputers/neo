from __future__ import annotations

"""Superadmin routes for provisioning outlets."""

from pathlib import Path
from uuid import uuid4
import asyncio
import subprocess
import sys

from fastapi import APIRouter
from pydantic import BaseModel

from utils.responses import ok
from utils.audit import audit
from .db.master import get_session
from .models_master import Tenant


router = APIRouter(prefix="/api/super")


class OutletPayload(BaseModel):
    """Payload for creating a new outlet."""

    name: str
    domain: str | None = None
    tz: str | None = None
    plan_tables: int | None = None


@router.post("/outlet")
@audit("create_outlet")
async def create_outlet(payload: OutletPayload) -> dict:
    """Provision a new tenant, persist it in master and initialise its DB."""

    tenant_uuid = uuid4()
    invoice_prefix = payload.name[:3].upper()
    async with get_session() as session:
        tenant = Tenant(
            id=tenant_uuid,
            name=payload.name,
            invoice_prefix=invoice_prefix,
            timezone=payload.tz,
            licensed_tables=payload.plan_tables or 0,
            status="active",
        )
        session.add(tenant)
        await session.commit()

    tenant_id = str(tenant_uuid)
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(scripts_dir / "tenant_create_db.py"), "--tenant", tenant_id],
        check=True,
    )
    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(scripts_dir / "tenant_migrate.py"), "--tenant", tenant_id],
        check=True,
    )
    return ok(
        {
            "tenant_id": tenant_id,
            "invoice_prefix": invoice_prefix,
            "tz": payload.tz,
            "licensed_tables": payload.plan_tables,
        }
    )

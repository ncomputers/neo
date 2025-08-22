from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from utils.responses import ok
from utils.audit import audit
from db.tenant import build_dsn


router = APIRouter(prefix="/api/super")


class OutletPayload(BaseModel):
    name: str
    domain: str | None = None
    tz: str | None = None
    plan_tables: int | None = None


@router.post("/outlet/check")
@audit("outlet_check")
async def outlet_check(payload: OutletPayload) -> dict:
    """Preview provisioning identifiers for a prospective tenant."""
    return ok(
        {
            "tenant_id_preview": str(uuid4()),
            "dsn_preview": build_dsn("<PREVIEW>"),
        }
    )

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .services import notifications
from .utils.responses import ok
from .utils.audit import audit

router = APIRouter()


class Breach(BaseModel):
    item: str
    avg_prep: float
    orders: int
    table: str | int


class SlaBreachIn(BaseModel):
    window: str
    breaches: list[Breach]


@router.post("/api/outlet/{tenant_id}/kds/sla/breach")
@audit("kds_sla_breach")
async def kds_sla_breach(tenant_id: str, payload: SlaBreachIn) -> dict:
    await notifications.enqueue(tenant_id, "sla_breach", payload.model_dump())
    return ok({})

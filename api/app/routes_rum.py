from __future__ import annotations

"""Routes for Real User Monitoring (Web Vitals)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from prometheus_client import Histogram
import uuid

from .deps.tenant import get_tenant_id
from .db import master
from .flags import get as get_flag
from .models_master import Tenant
from .utils.responses import ok

router = APIRouter(prefix="/rum")

# Histograms for Web Vitals
lcp_hist = Histogram(
    "web_vitals_lcp_seconds",
    "Largest Contentful Paint (s)",
    ["ctx"],
    buckets=(0.5, 1, 2.5, 4, 6, 10),
)
cls_hist = Histogram(
    "web_vitals_cls",
    "Cumulative Layout Shift",
    ["ctx"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2),
)
inp_hist = Histogram(
    "web_vitals_inp_seconds",
    "Interaction to Next Paint (s)",
    ["ctx"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 4, 6, 10),
)


class VitalsPayload(BaseModel):
    ctx: str = "guest"
    lcp: float | None = None
    cls: float | None = None
    inp: float | None = None
    consent: bool = False


async def _analytics_enabled(tenant_id: str) -> bool:
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        tid = None
    tenant = None
    if tid is not None:
        async with master.get_session() as session:
            tenant = await session.get(Tenant, tid)
    return get_flag("analytics", tenant)


@router.post("/vitals")
async def collect_vitals(
    payload: VitalsPayload,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    if not payload.consent or not await _analytics_enabled(tenant_id):
        return ok({})

    labels = {"ctx": payload.ctx}
    if payload.lcp is not None:
        lcp_hist.labels(**labels).observe(payload.lcp)
    if payload.cls is not None:
        cls_hist.labels(**labels).observe(payload.cls)
    if payload.inp is not None:
        inp_hist.labels(**labels).observe(payload.inp)
    return ok({})


__all__ = ["router"]

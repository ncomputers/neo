from __future__ import annotations

"""Routes for Real User Monitoring (Web Vitals)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, validator
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
    ["route"],
    buckets=(0.5, 1, 2.5, 4, 6, 10),
)
cls_hist = Histogram(
    "web_vitals_cls",
    "Cumulative Layout Shift",
    ["route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2),
)
inp_hist = Histogram(
    "web_vitals_inp_seconds",
    "Interaction to Next Paint (s)",
    ["route"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 4, 6, 10),
)
ttfb_hist = Histogram(
    "web_vitals_ttfb_seconds",
    "Time to First Byte (s)",
    ["route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 4),
)


ROUTE_WHITELIST = {
    "/",
    "/guest",
    "/dashboard",
    "/admin",
    "/admin/troubleshoot",
    "/billing",
    "/cashier",
    "/expo",
    "/kitchen",
    "/cleaner",
    "/login",
}


class VitalsPayload(BaseModel):
    route: str
    lcp: float | None = Field(default=None, ge=0, le=10)
    cls: float | None = Field(default=None, ge=0, le=2)
    inp: float | None = Field(default=None, ge=0, le=10)
    ttfb: float | None = Field(default=None, ge=0, le=4)
    consent: bool = False

    @validator("route")
    def _sanitize_route(cls, v: str) -> str:  # noqa: N805 - pydantic validator
        path = v.split("?")[0]
        if len(path) > 64:
            raise ValueError("route too long")
        for allowed in sorted(ROUTE_WHITELIST, key=len, reverse=True):
            if path == allowed or path.startswith(allowed + "/"):
                return allowed
        raise ValueError("invalid route")


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

    labels = {"route": payload.route}
    if payload.lcp is not None:
        lcp_hist.labels(**labels).observe(payload.lcp)
    if payload.cls is not None:
        cls_hist.labels(**labels).observe(payload.cls)
    if payload.inp is not None:
        inp_hist.labels(**labels).observe(payload.inp)
    if payload.ttfb is not None:
        ttfb_hist.labels(**labels).observe(payload.ttfb)
    return ok({})


__all__ = ["router"]

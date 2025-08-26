from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query

from .auth import User, authenticate_user
from .exp.ab_allocator import get_variant
from .routes_metrics import ab_exposures_total

router = APIRouter()


@router.get("/api/ab/{experiment}")
async def fetch_variant(
    experiment: str,
    device_id_header: str | None = Header(None, alias="device-id"),
    device_id_query: str | None = Query(None, alias="device_id"),
    user: User = Depends(authenticate_user),
) -> dict:
    """Return assigned variant for ``experiment`` and ``device_id``.

    ``device_id`` may be supplied via the ``device-id`` header or
    ``device_id`` query parameter.
    """
    device_id = device_id_header or device_id_query or ""
    variant = get_variant(device_id, experiment)
    ab_exposures_total.labels(experiment=experiment, variant=variant).inc()
    return {"variant": variant}

from __future__ import annotations

"""Operations admin routes."""

import os

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")


@router.get("/admin/ops/slo")
async def slo_error_budget() -> dict[str, dict[str, float]]:
    """Return 30‑day error budget by route."""
    query = (
        "sum(increase(slo_errors_total[30d])) by (route) / "
        "sum(increase(slo_requests_total[30d])) by (route)"
    )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{PROM_URL}/api/v1/query", params={"query": query})
        data = resp.json()
    except httpx.HTTPError as exc:  # pragma: no cover - network errors
        raise HTTPException(status_code=502, detail="prometheus unreachable") from exc
    if data.get("status") != "success":
        raise HTTPException(status_code=502, detail="prometheus query failed")
    result: dict[str, dict[str, float]] = {}
    for item in data.get("data", {}).get("result", []):
        route = item.get("metric", {}).get("route", "")
        error_rate = float(item.get("value", [0, 0])[1])
        result[route] = {
            "error_rate": error_rate,
            "error_budget": max(0.0, 1 - error_rate),
        }
    return result

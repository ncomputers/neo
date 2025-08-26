from __future__ import annotations

import json
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends, Query, Request, Response

from .staff_auth import role_required
from .utils.responses import ok

router = APIRouter()

_CSP_KEY = "csp:reports"
_MAX_REPORTS = 500
_TTL = 86400


def _redact_url(url: str) -> str:
    """Strip query/fragment components from a URL."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


@router.post("/csp/report", status_code=204)
async def csp_report(request: Request) -> Response:
    redis = request.app.state.redis
    body = await request.body()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        payload = body.decode()
    else:
        report = data.get("csp-report") if isinstance(data, dict) else None
        if isinstance(report, dict):
            for key, value in list(report.items()):
                if isinstance(value, str):
                    if "token" in key.lower():
                        report[key] = "***"
                    else:
                        report[key] = _redact_url(value)
        payload = json.dumps(data, separators=(",", ":"))

    await redis.rpush(_CSP_KEY, payload)
    await redis.ltrim(_CSP_KEY, -_MAX_REPORTS, -1)
    await redis.expire(_CSP_KEY, _TTL)
    return Response(status_code=204)


@router.get("/admin/csp/reports")
async def get_csp_reports(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=_MAX_REPORTS),
    staff=Depends(role_required("admin", "super_admin")),
):
    redis = request.app.state.redis
    end = offset + limit - 1
    items = await redis.lrange(_CSP_KEY, offset, end)
    reports = [json.loads(i) for i in items]
    return ok(reports)


__all__ = ["router"]

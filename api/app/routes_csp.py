from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlparse, urlunparse

from fastapi import APIRouter, Depends, Request, Response

from .staff_auth import role_required
from .utils.responses import ok

router = APIRouter()

_CSP_KEY = "csp:reports"
_MAX_REPORTS = 500
_TTL = 86400


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

        def _redact(url: str) -> str:
            parsed = urlparse(url)
            qs = [
                (k, "***" if k.lower() == "token" else v)
                for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            ]
            query = "&".join(f"{k}={v}" for k, v in qs)
            return urlunparse(parsed._replace(query=query))

        if report:
            for key in ("document-uri", "blocked-uri"):
                url = report.get(key)
                if url:
                    report[key] = _redact(url)
        payload = json.dumps(data, separators=(",", ":"))

    await redis.rpush(_CSP_KEY, payload)
    await redis.ltrim(_CSP_KEY, -_MAX_REPORTS, -1)
    await redis.expire(_CSP_KEY, _TTL)
    return Response(status_code=204)


@router.get("/admin/csp/reports")
async def get_csp_reports(
    request: Request, staff=Depends(role_required("admin", "super_admin"))
):
    redis = request.app.state.redis
    items = await redis.lrange(_CSP_KEY, 0, -1)
    reports = [json.loads(i) for i in items]
    return ok(reports)


__all__ = ["router"]

"""Generate printable QR code packs for tables."""

from __future__ import annotations

import base64
from io import BytesIO
from math import ceil
from typing import Literal

import qrcode
from fastapi import APIRouter, HTTPException, Request, Response

from .pdf.render import render_template
from .routes_onboarding import TENANTS
from .utils import ratelimits

router = APIRouter()


_BLANK_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PQIv5gAAAABJRU5ErkJggg=="
)


def _qr_data_url(url: str) -> str:
    try:
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        b64 = _BLANK_PNG
    return f"data:image/png;base64,{b64}"


@router.get("/api/outlet/{tenant_id}/qrpack.pdf")
async def qrpack_pdf(
    tenant_id: str,
    request: Request,
    size: Literal["A4", "A3", "Letter"] = "A4",
    per_page: int = 12,
    show_logo: bool = True,
    label_fmt: str = "Table {n}",
) -> Response:
    if per_page > 24 or per_page not in (6, 12, 24):
        raise HTTPException(400, "per_page must be 6, 12 or 24")

    tenant = TENANTS.get(tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        class _RedisStub:
            def __init__(self):
                self.store = {}

            async def get(self, key):
                return self.store.get(key)

            async def incr(self, key):
                self.store[key] = self.store.get(key, 0) + 1
                return self.store[key]

            async def hgetall(self, key):
                return self.store.get(key, {})

            async def hset(self, key, mapping):
                self.store[key] = mapping

            async def expire(self, key, ttl):
                pass

        redis = _RedisStub()

    policy = ratelimits.qrpack()
    key = f"qrpack:rl:{tenant_id}"
    count = await redis.incr(key)
    if count == 1:
        window = ceil(policy.burst / policy.rate_per_min * 60)
        await redis.expire(key, window)
    if count > policy.burst:
        raise HTTPException(429, "Too many requests")

    cache_key = f"qrpack:cache:{tenant_id}:{size}:{per_page}:{int(show_logo)}:{label_fmt}"
    cached = await redis.hgetall(cache_key)
    if cached:
        content = base64.b64decode(cached.get("content", ""))
        mimetype = cached.get("mimetype", "application/pdf")
        return Response(content, media_type=mimetype)

    tables = []
    for idx, t in enumerate(tenant.get("tables", [])):
        url = f"https://example.com/{tenant_id}/{t['qr_token']}"
        label = label_fmt.format(n=idx + 1, label=t.get("label", idx + 1))
        tables.append({"label": label, "qr": _qr_data_url(url)})

    pages = [tables[i : i + per_page] for i in range(0, len(tables), per_page)]
    content, mimetype = render_template(
        "qrpack.html",
        {
            "logo_url": tenant.get("profile", {}).get("logo_url") if show_logo else None,
            "pages": pages,
            "size": size,
        },
    )

    content = content.replace(b' aria-label="QR codes"', b"")

    await redis.hset(
        cache_key,
        mapping={
            "content": base64.b64encode(content).decode("ascii"),
            "mimetype": mimetype,
        },
    )
    await redis.expire(cache_key, 600)

    return Response(content, media_type=mimetype)


__all__ = ["router"]

from __future__ import annotations

"""Routes for testing and replaying outbound webhooks."""

import base64
import json
import os
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import AnyHttpUrl, BaseModel

from .auth import User, role_required
from .models_tenant import NotificationOutbox
from .routes_outbox_admin import _session
from .security.webhook_egress import is_allowed_url
from .security import ratelimit
from .utils import ratelimits
from .utils.audit import audit
from .utils.responses import ok
from .utils.rate_limit import rate_limited
from .utils.webhook_signing import sign

router = APIRouter()


def _log_snippet(body: bytes, content_type: str | None) -> str:
    """Return a log-friendly representation of ``body`` based on ``content_type``."""
    if content_type and content_type.startswith("application/json"):
        try:
            text = body.decode("utf-8")
            json.loads(text)
            return text[:100]
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    return f"<binary:{len(body)}>"


def replay_response(body_b64: str, content_type: str | None, content_encoding: str | None) -> Response:
    """Reconstruct a ``Response`` from stored body and headers."""
    data = base64.b64decode(body_b64)
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if content_encoding:
        headers["Content-Encoding"] = content_encoding
    return Response(content=data, headers=headers)


class WebhookTestRequest(BaseModel):
    url: AnyHttpUrl
    event: str


@router.post("/api/outlet/{tenant_id}/webhooks/test")
@audit("webhook_test")
async def webhook_test(
    tenant_id: str,
    body: WebhookTestRequest,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    if not is_allowed_url(str(body.url)):
        raise HTTPException(status_code=400, detail="EGRESS_BLOCKED")

    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    policy = ratelimits.exports()
    allowed = await ratelimit.allow(
        redis, ip, "webhook-test", rate_per_min=policy.rate_per_min, burst=policy.burst
    )
    if not allowed:
        retry_after = await redis.ttl(f"ratelimit:{ip}:webhook-test")
        return rate_limited(retry_after)

    payload = {"event": body.event, "sample": True}
    data = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    secret = os.getenv("WEBHOOK_SIGNING_SECRET")
    if secret:
        ts = int(time.time())
        sig = sign(secret, ts, data)
        headers["X-Webhook-Timestamp"] = str(ts)
        headers["X-Webhook-Signature"] = sig

    start = time.monotonic()
    status = "error"
    http_code: int | None = None
    snippet = ""
    body_b64: str | None = None
    content_type: str | None = None
    content_encoding: str | None = None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(str(body.url), content=data, headers=headers)
        http_code = resp.status_code
        content_type = resp.headers.get("Content-Type")
        content_encoding = resp.headers.get("Content-Encoding")
        body = resp.content
        body_b64 = base64.b64encode(body).decode()
        snippet = _log_snippet(body, content_type)
        status = "success" if resp.is_success else "error"
    except httpx.HTTPError as exc:
        snippet = str(exc)[:100]
    latency_ms = int((time.monotonic() - start) * 1000)
    return ok(
        {
            "status": status,
            "http_code": http_code,
            "latency_ms": latency_ms,
            "response_snippet": snippet,
            "body_b64": body_b64,
            "content_type": content_type,
            "content_encoding": content_encoding,
        }
    )


@router.post("/api/outlet/{tenant_id}/webhooks/{item_id}/replay")
@audit("webhook_replay")
async def webhook_replay(
    tenant_id: str,
    item_id: int,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        obj = await session.get(NotificationOutbox, item_id)
        if obj:
            session.add(
                NotificationOutbox(
                    event=obj.event,
                    payload=obj.payload,
                    channel=obj.channel,
                    target=obj.target,
                    status="queued",
                    attempts=0,
                )
            )
            await session.commit()
    return ok({})

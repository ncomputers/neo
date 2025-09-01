from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS

from ..audit import log_event
from ..security.pin_lockout import is_locked
from ..security.pin_lockout import keys as lock_keys
from ..security.pin_lockout import register_failure
from ..utils.responses import err

ROTATE_DAYS = 90
WARN_DAYS = 80


async def record_pin_rotation(redis: Any, tenant: str, username: str) -> None:
    """Record a PIN rotation time and audit the event."""

    await redis.set(f"pin:rot:{tenant}:{username}", datetime.utcnow().isoformat())
    log_event(username, "pin_rotate", tenant)


class PinSecurityMiddleware(BaseHTTPMiddleware):
    """Enforce PIN login security policies."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if not (request.url.path == "/login/pin" and request.method == "POST"):
            return await call_next(request)

        redis = request.app.state.redis
        tenant = request.headers.get("X-Tenant-ID", "demo")
        ip = request.client.host if request.client else "unknown"

        body = await request.body()
        try:
            data = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            data = {}
        username = data.get("username", "")

        lock_key, status_key, fail_key = lock_keys(tenant, username, ip)
        rot_key = f"pin:rot:{tenant}:{username}"

        if await is_locked(redis, tenant, username, ip):
            return JSONResponse(
                err("AUTH_LOCKED", "AuthLocked"), status_code=HTTP_403_FORBIDDEN
            )

        if await redis.exists(status_key) and not await is_locked(
            redis, tenant, username, ip
        ):
            await redis.delete(status_key)
            await redis.delete(fail_key)
            log_event(username, "pin_unlock", tenant)

        warn = False
        rot_val = await redis.get(rot_key)
        if rot_val:
            if isinstance(rot_val, bytes):
                rot_val = rot_val.decode()
            last = datetime.fromisoformat(rot_val)
            age = (datetime.utcnow() - last).days
            if age >= ROTATE_DAYS:
                return JSONResponse(
                    err("PIN_EXPIRED", "PinExpired"),
                    status_code=HTTP_403_FORBIDDEN,
                )
            if age >= WARN_DAYS:
                warn = True

        async def receive() -> dict:
            return {"type": "http.request", "body": body}

        request._receive = receive  # type: ignore[attr-defined]
        response = await call_next(request)

        if response.status_code == HTTP_429_TOO_MANY_REQUESTS:
            return response

        if response.status_code != 200:
            locked = await register_failure(redis, tenant, username, ip)
            if locked:
                log_event(username, "pin_lock", tenant)
            return response

        await redis.delete(fail_key)
        if warn and response.headers.get("content-type", "").startswith(
            "application/json"
        ):
            payload = json.loads(response.body.decode())
            data = payload.get("data", {})
            data["rotation_warning"] = True
            payload["data"] = data
            response = JSONResponse(payload, status_code=response.status_code)
        return response

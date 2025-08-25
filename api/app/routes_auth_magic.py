from __future__ import annotations

"""Passwordless owner authentication via email magic links."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from .auth import ALGORITHM, SECRET_KEY, Token, create_access_token
from .providers import email_stub
from .security import ratelimit
from .utils.responses import err, ok

router = APIRouter()


class StartPayload(BaseModel):
    """Email address requesting a magic link."""

    email: EmailStr


@router.post("/auth/magic/start")
async def magic_start(payload: StartPayload, request: Request) -> dict:
    """Begin magic-link login and email a one-time token."""

    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    email = payload.email.lower()

    allowed_ip = await ratelimit.allow(
        redis, ip, "magic-start", rate_per_min=3, burst=3
    )
    if not allowed_ip:
        retry_after = await redis.ttl(f"ratelimit:{ip}:magic-start")
        return JSONResponse(
            err("RATELIMITED", "TooManyRequests", {"retry_after": max(retry_after, 0)}),
            status_code=HTTP_429_TOO_MANY_REQUESTS,
        )

    allowed_email = await ratelimit.allow(
        redis, email, "magic-email", rate_per_min=10 / 60, burst=10
    )
    if not allowed_email:
        retry_after = await redis.ttl(f"ratelimit:{email}:magic-email")
        return JSONResponse(
            err("RATELIMITED", "TooManyRequests", {"retry_after": max(retry_after, 0)}),
            status_code=HTTP_429_TOO_MANY_REQUESTS,
        )

    jti = str(uuid.uuid4())
    token = create_access_token(
        {"sub": email, "jti": jti, "scope": "magic"},
        expires_delta=timedelta(minutes=15),
    )
    await redis.setex(f"magic:{jti}", 15 * 60, email)
    email_stub.send("magic_link", {"subject": "Magic login", "token": token}, email)
    return ok({"token": token})


@router.get("/auth/magic/consume")
async def magic_consume(token: str, request: Request) -> dict:
    """Redeem a magic link token and return a session JWT."""

    redis = request.app.state.redis
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid token") from exc

    if payload.get("scope") != "magic":
        raise HTTPException(status_code=400, detail="Invalid token")

    jti = payload.get("jti")
    email = payload.get("sub")
    if not jti or not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    stored = await redis.get(f"magic:{jti}")
    if isinstance(stored, bytes):
        stored = stored.decode()
    if stored != email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await redis.delete(f"magic:{jti}")
    session = create_access_token({"sub": email, "role": "owner"})
    return ok(Token(access_token=session, role="owner"))


__all__ = ["router"]

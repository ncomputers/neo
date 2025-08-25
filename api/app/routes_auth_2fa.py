from __future__ import annotations

"""TOTP-based optional two-factor authentication for owners and admins."""

import base64
import hashlib
import hmac
import io
import os
import secrets
import struct
import time
from datetime import datetime

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .audit import log_event
from .auth import User, role_required
from .db import SessionLocal
from .models_master import TwoFactorBackupCode, TwoFactorSecret
from .security import ratelimit
from .utils import ratelimits
from .utils.responses import err, ok

router = APIRouter()


def _b32_secret() -> str:
    seed = hashlib.sha256(os.urandom(32)).digest()
    return base64.b32encode(seed).decode().strip("=")


def _qr_data_uri(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _totp_now(secret: str, counter: int | None = None) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    counter = counter if counter is not None else int(time.time() / 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    ) % 1_000_000
    return f"{code:06d}"


def _verify_totp(secret: str, code: str) -> bool:
    counter = int(time.time() / 30)
    for delta in (-1, 0, 1):
        if _totp_now(secret, counter + delta) == code:
            return True
    return False


class CodePayload(BaseModel):
    code: str


@router.post("/auth/2fa/setup")
async def setup_2fa(user: User = Depends(role_required("owner", "super_admin"))):
    secret = _b32_secret()
    uri = f"otpauth://totp/Neo:{user.username}?secret={secret}&issuer=Neo"
    qr = _qr_data_uri(uri)
    with SessionLocal() as db:
        existing = db.get(TwoFactorSecret, user.username)
        if existing:
            db.query(TwoFactorBackupCode).filter_by(user=user.username).delete()
            db.delete(existing)
        db.add(TwoFactorSecret(user=user.username, secret=secret))
        db.commit()
    log_event(user.username, "2FA_SETUP", "user", master=True)
    return ok({"otpauth": uri, "qr": qr, "secret": secret})


@router.post("/auth/2fa/enable")
async def enable_2fa(
    payload: CodePayload, user: User = Depends(role_required("owner", "super_admin"))
):
    with SessionLocal() as db:
        record = db.get(TwoFactorSecret, user.username)
        if not record:
            raise HTTPException(status_code=400, detail="2FA not setup")
        if not _verify_totp(record.secret, payload.code):
            raise HTTPException(status_code=400, detail="Invalid code")
        record.confirmed_at = datetime.utcnow()
        db.commit()
    log_event(user.username, "2FA_ENABLED", "user", master=True)
    return ok({"enabled": True})


@router.post("/auth/2fa/disable")
async def disable_2fa(
    payload: CodePayload, user: User = Depends(role_required("owner", "super_admin"))
):
    with SessionLocal() as db:
        record = db.get(TwoFactorSecret, user.username)
        if not record or not record.confirmed_at:
            raise HTTPException(status_code=400, detail="2FA not enabled")
        valid = _verify_totp(record.secret, payload.code)
        if not valid:
            code_hash = hashlib.sha256(payload.code.encode()).hexdigest()
            backup = (
                db.query(TwoFactorBackupCode)
                .filter_by(user=user.username, code_hash=code_hash, used_at=None)
                .first()
            )
            if not backup:
                raise HTTPException(status_code=400, detail="Invalid code")
            backup.used_at = datetime.utcnow()
        db.query(TwoFactorBackupCode).filter_by(user=user.username).delete()
        db.delete(record)
        db.commit()
    log_event(user.username, "2FA_DISABLED", "user", master=True)
    return ok({"disabled": True})


@router.post("/auth/2fa/verify")
async def verify_2fa(
    payload: CodePayload,
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
):
    redis = request.app.state.redis
    ip = request.client.host if request.client else "unknown"
    policy = ratelimits.two_factor_verify()
    allowed = await ratelimit.allow(
        redis, ip, "2fa-verify", rate_per_min=policy.rate_per_min, burst=policy.burst
    )
    if not allowed:
        retry_after = await redis.ttl(f"ratelimit:{ip}:2fa-verify")
        return JSONResponse(
            err("RATELIMITED", "TooManyRequests", {"retry_after": max(retry_after, 0)}),
            status_code=429,
        )
    with SessionLocal() as db:
        record = db.get(TwoFactorSecret, user.username)
        if not record or not record.confirmed_at:
            raise HTTPException(status_code=400, detail="2FA not enabled")
        if _verify_totp(record.secret, payload.code):
            log_event(user.username, "2FA_VERIFY_OK", "user", master=True)
            return ok({"verified": True})
        code_hash = hashlib.sha256(payload.code.encode()).hexdigest()
        backup = (
            db.query(TwoFactorBackupCode)
            .filter_by(user=user.username, code_hash=code_hash, used_at=None)
            .first()
        )
        if backup:
            backup.used_at = datetime.utcnow()
            db.commit()
            log_event(user.username, "2FA_VERIFY_BACKUP", "user", master=True)
            return ok({"verified": True})
    log_event(user.username, "2FA_VERIFY_FAIL", "user", master=True)
    raise HTTPException(status_code=400, detail="Invalid code")


@router.get("/auth/2fa/backup")
async def backup_codes(user: User = Depends(role_required("owner", "super_admin"))):
    with SessionLocal() as db:
        record = db.get(TwoFactorSecret, user.username)
        if not record or not record.confirmed_at:
            raise HTTPException(status_code=400, detail="2FA not enabled")
        db.query(TwoFactorBackupCode).filter_by(user=user.username).delete()
        codes = [secrets.token_hex(4) for _ in range(10)]
        for code in codes:
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            db.add(TwoFactorBackupCode(user=user.username, code_hash=code_hash))
        db.commit()
    log_event(user.username, "2FA_BACKUP", "user", master=True)
    return ok({"codes": codes})


__all__ = ["router"]

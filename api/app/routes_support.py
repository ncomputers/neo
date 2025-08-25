# routes_support.py
"""Support diagnostics bundle route."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.master import get_session
from .db.tenant import get_engine
from .middlewares.licensing import PLAN_FEATURES
from .models_master import Tenant
from .models_tenant import AuditTenant

router = APIRouter()

admin_required = role_required("super_admin")


@asynccontextmanager
async def _tenant_session(tenant_id: str):
    """Yield an ``AsyncSession`` for ``tenant_id``."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


def _mask(value: str) -> str:
    """Return a masked representation of ``value``."""
    if not value:
        return ""
    return value[:4] + "****"


def _env_dump() -> str:
    """Collect selected environment variables with masked values."""
    prefixes = ("APP_", "POSTGRES_", "REDIS_", "SENTRY_", "GIT_", "ENV", "LOG_LEVEL")
    lines: list[str] = []
    for key, val in os.environ.items():
        if key.startswith(prefixes):
            lines.append(f"{key}={_mask(val)}")
    return "\n".join(sorted(lines))


async def _recent_logs(tenant_id: str) -> str:
    """Return recent logs or last 200 audit entries."""
    log_path = Path("recent.log")
    if log_path.exists():
        try:
            return log_path.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover - best effort
            pass
    try:
        async with _tenant_session(tenant_id) as session:
            stmt = (
                select(AuditTenant.actor, AuditTenant.action, AuditTenant.at)
                .order_by(AuditTenant.id.desc())
                .limit(200)
            )
            rows = (await session.execute(stmt)).all()
    except Exception:  # pragma: no cover - DB errors fall through
        rows = []
    lines = [
        f"{at.isoformat()} {actor} {action}" for actor, action, at in reversed(rows)
    ]
    return "\n".join(lines)


async def _get_config(tenant_id: str) -> dict:
    """Return basic config details for ``tenant_id``."""
    try:
        async with get_session() as session:
            tenant = await session.get(Tenant, tenant_id)
    except Exception:  # pragma: no cover - best effort
        tenant = None
    if tenant:
        plan = getattr(tenant, "plan", "starter")
        flags = {
            "gst_mode": tenant.gst_mode,
            "enable_hotel": tenant.enable_hotel,
            "enable_counter": tenant.enable_counter,
        }
    else:
        plan = "unknown"
        flags = {}
    return {"plan": plan, "features": PLAN_FEATURES.get(plan, {}), "flags": flags}


@router.get("/api/outlet/{tenant_id}/support/bundle.zip")
async def support_bundle(
    tenant_id: str, user: User = Depends(admin_required)
) -> Response:
    """Return a diagnostic ZIP bundle for ``tenant_id``."""
    env_txt = _env_dump()
    health_json = {"status": "ok"}
    ready_json = {"ok": True}
    version_json = {
        "app": "neo",
        "sha": os.getenv("GIT_SHA", "unknown"),
        "built_at": os.getenv("BUILT_AT", "unknown"),
    }
    logs_txt = await _recent_logs(tenant_id)
    config_json = await _get_config(tenant_id)

    bundle = BytesIO()
    with ZipFile(bundle, "w") as zf:
        zf.writestr("env.txt", env_txt)
        zf.writestr("health.json", json.dumps(health_json))
        zf.writestr("ready.json", json.dumps(ready_json))
        zf.writestr("version.json", json.dumps(version_json))
        zf.writestr("recent-logs.txt", logs_txt)
        zf.writestr("config.json", json.dumps(config_json))
    return Response(bundle.getvalue(), media_type="application/zip")

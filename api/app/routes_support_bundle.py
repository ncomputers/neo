"""Tenant support bundle export."""
from __future__ import annotations

import json
import os
from io import BytesIO
from zipfile import ZipFile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .audit import Audit, SessionLocal
from .auth import User, role_required
from .db.master import get_session
from .models_master import Tenant
from .routes_ready import ready
from .routes_version import version
from .utils.responses import ok

router = APIRouter()

_ENV_KEYS = ["LOG_LEVEL", "LOG_FORMAT", "REDIS_URL"]


def _mask(value: str | None) -> str:
    if not value:
        return ""
    return "****"


async def _bundle_stream(tenant: Tenant):
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        env_lines = [f"{k}={_mask(os.getenv(k))}" for k in _ENV_KEYS]
        zf.writestr("env.txt", "\n".join(env_lines))

        health_data = ok({"status": "ok"})
        ready_data = await ready()
        version_data = await version()
        zf.writestr("health.json", json.dumps(health_data))
        zf.writestr("ready.json", json.dumps(ready_data))
        zf.writestr("version.json", json.dumps(version_data))

        config = {
            "plan": (getattr(tenant, "license_limits", {}) or {}).get("plan"),
            "feature_flags": {
                "hotel": getattr(tenant, "enable_hotel", False),
                "counter": getattr(tenant, "enable_counter", False),
            },
            "tz": getattr(tenant, "timezone", os.getenv("DEFAULT_TZ", "UTC")),
            "licensing": {
                "licensed_tables": getattr(tenant, "licensed_tables", 0),
            },
        }
        zf.writestr("config.json", json.dumps(config))

        with SessionLocal() as session:
            rows = session.query(Audit).order_by(Audit.id.desc()).limit(200).all()
            audit_entries = [
                {
                    "actor": r.actor,
                    "action": r.action,
                    "entity": r.entity,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        zf.writestr("recent_audit.json", json.dumps(audit_entries))

        log_file = os.getenv("LOG_FILE")
        if log_file:
            try:
                with open(log_file, "r", encoding="utf-8") as fh:
                    tail = fh.readlines()[-200:]
                zf.writestr("recent-logs.txt", "".join(tail))
            except Exception:
                pass

    buf.seek(0)
    yield buf.getvalue()


@router.get("/api/outlet/{tenant_id}/support/bundle.zip")
async def support_bundle(
    tenant_id: str,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> StreamingResponse:
    async with get_session() as session:
        tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    headers = {"Content-Disposition": f"attachment; filename={tenant_id}_bundle.zip"}
    return StreamingResponse(
        _bundle_stream(tenant), media_type="application/zip", headers=headers
    )

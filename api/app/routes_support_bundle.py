"""Support bundle generation."""

from __future__ import annotations

import json
import os
from io import BytesIO
from typing import Iterator
from zipfile import ZipFile

from fastapi import APIRouter, Depends
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


@router.get("/api/outlet/{tenant_id}/support/bundle.zip")
async def support_bundle(
    tenant_id: str,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> StreamingResponse:
    ready_data = await ready()
    version_data = await version()
    health_data = ok({"status": "ok"})

    async with get_session() as session:
        tenant = await session.get(Tenant, tenant_id)

    config = {}
    if tenant:
        config = {
            "plan": (tenant.license_limits or {}).get("plan"),
            "feature_flags": {
                "enable_hotel": bool(tenant.enable_hotel),
                "enable_counter": bool(tenant.enable_counter),
                "enable_gateway": bool(getattr(tenant, "enable_gateway", False)),

                "sla_sound_alert": bool(tenant.sla_sound_alert),
                "sla_color_alert": bool(tenant.sla_color_alert),
            },
            "tz": tenant.timezone or os.getenv("DEFAULT_TZ", "UTC"),
            "licensing": {"licensed_tables": tenant.licensed_tables},
        }

    with SessionLocal() as session:
        rows = session.query(Audit).order_by(Audit.id.desc()).limit(200).all()
        audit_data = [
            {
                "created_at": r.created_at.isoformat(),
                "actor": r.actor,
                "action": r.action,
                "entity": r.entity,
            }
            for r in rows
        ]

    log_content = None
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            with open(log_file, "r", encoding="utf-8") as fh:
                lines = fh.readlines()[-200:]
            log_content = "".join(lines)
        except Exception:  # pragma: no cover - best effort
            log_content = None

    def build_zip() -> Iterator[bytes]:
        buffer = BytesIO()
        with ZipFile(buffer, "w") as zf:
            env_lines = [f"{k}={_mask(os.getenv(k))}" for k in _ENV_KEYS]
            zf.writestr("env.txt", "\n".join(env_lines))
            zf.writestr("health.json", json.dumps(health_data))
            zf.writestr("ready.json", json.dumps(ready_data))
            zf.writestr("version.json", json.dumps(version_data))
            zf.writestr("config.json", json.dumps(config))
            zf.writestr("recent_audit.json", json.dumps(audit_data))
            if log_content:
                zf.writestr("logs.txt", log_content)
        buffer.seek(0)
        while chunk := buffer.read(8192):
            yield chunk

    headers = {"Content-Disposition": f"attachment; filename={tenant_id}_bundle.zip"}
    return StreamingResponse(build_zip(), media_type="application/zip", headers=headers)

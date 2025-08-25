from __future__ import annotations

"""Support contact and bundle export endpoints."""


import json
import os
from io import BytesIO
from zipfile import ZipFile

from fastapi import APIRouter, Depends, Response

from .audit import Audit, SessionLocal
from .auth import User, role_required
from .db.master import get_session
from .models_master import Tenant
from .routes_ready import ready
from .routes_version import version
from .utils.responses import ok

router = APIRouter()


@router.get("/support/contact")
async def support_contact() -> dict:
    """Return support contact details."""
    return {
        "email": "support@example.com",
        "phone": "+1-800-555-0199",
        "hours": "09:00-18:00 IST",
        "docs_url": "https://docs.example.com",
    }


_ENV_KEYS = ["LOG_LEVEL", "LOG_FORMAT", "REDIS_URL"]


def _mask(value: str | None) -> str:
    if not value:
        return ""
    return "****"


@router.get("/api/outlet/{tenant_id}/support/bundle.zip")
async def support_bundle(
    tenant_id: str,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> Response:
    bundle = BytesIO()
    with ZipFile(bundle, "w") as zf:
        env_lines = [f"{k}={_mask(os.getenv(k))}" for k in _ENV_KEYS]
        zf.writestr("env.txt", "\n".join(env_lines))
        health_data = ok({"status": "ok"})
        ready_data = await ready()
        version_data = await version()
        zf.writestr("health.json", json.dumps(health_data))
        zf.writestr("ready.json", json.dumps(ready_data))
        zf.writestr("version.json", json.dumps(version_data))

        log_file = os.getenv("LOG_FILE", "app.log")
        logs = ""
        try:
            with open(log_file, "r", encoding="utf-8") as fh:
                logs = fh.read()
        except Exception:
            with SessionLocal() as session:
                rows = session.query(Audit).order_by(Audit.id.desc()).limit(200).all()
                lines = [
                    f"{r.created_at}\t{r.actor}\t{r.action}\t{r.entity}" for r in rows
                ]
                logs = "\n".join(lines)
        zf.writestr("recent-logs.txt", logs)
        async with get_session() as session:
            if hasattr(session, "query"):
                audit_rows = session.query(Audit).order_by(Audit.id.desc()).limit(200)
                logs = "\n".join(a.message for a in audit_rows)
            else:  # pragma: no cover - test stubs
                logs = ""
        zf.writestr("recent-logs.txt", logs)
        zf.writestr("config.json", json.dumps({}))
    headers = {
        "Content-Disposition": f"attachment; filename={tenant_id}_bundle.zip",
        "Content-Type": "application/zip",
    }
    return Response(bundle.getvalue(), headers=headers)

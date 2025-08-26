from __future__ import annotations

"""Operational preflight checklist endpoint."""

import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import APIRouter, UploadFile
from sqlalchemy import text

from .db import SessionLocal, engine
from .storage import storage

router = APIRouter()


async def check_db() -> dict:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"name": "db", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "db", "status": "fail", "detail": str(exc)}


async def check_redis() -> dict:
    try:
        from .main import redis_client

        if redis_client is not None:
            await redis_client.ping()
        return {"name": "redis", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "redis", "status": "fail", "detail": str(exc)}


def check_migrations() -> dict:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", str(engine.url))
        script = ScriptDirectory.from_config(cfg)
        head = script.get_current_head()
        with engine.connect() as conn:
            current = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        status = "ok" if current == head else "fail"
        detail = None if status == "ok" else f"current={current} head={head}"
        result = {"name": "migrations", "status": status}
        if detail:
            result["detail"] = detail
        return result
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "migrations", "status": "fail", "detail": str(exc)}


async def check_storage() -> dict:
    try:
        dummy = UploadFile(filename="ping.txt", file=BytesIO(b"ping"))
        url, key = await storage.save("__preflight__", dummy)
        storage.read(key)
        return {"name": "storage", "status": "ok", "detail": url}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "storage", "status": "fail", "detail": str(exc)}


def check_webhooks() -> dict:
    disabled = os.getenv("DISABLE_WEBHOOKS", "0").lower() in {"1", "true"}
    status = "warn" if disabled else "ok"
    detail = "disabled" if disabled else None
    result = {"name": "webhooks", "status": status}
    if detail:
        result["detail"] = detail
    return result


async def check_alertmanager() -> dict:
    url = os.getenv("ALERTMANAGER_URL")
    if not url:
        return {"name": "alertmanager", "status": "warn", "detail": "missing"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.get(url)
        return {"name": "alertmanager", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "alertmanager", "status": "warn", "detail": str(exc)}


def check_backups() -> dict:
    backups_dir = Path(__file__).resolve().parents[2] / "backups"
    newest = 0.0
    if backups_dir.exists():
        files = list(backups_dir.glob("*.json"))
        if files:
            newest = max(f.stat().st_mtime for f in files)
    if not newest:
        return {"name": "backups", "status": "warn", "detail": "missing"}
    age = datetime.now(tz=timezone.utc).timestamp() - newest
    status = "ok" if age < 24 * 3600 else "warn"
    result = {"name": "backups", "status": status}
    if status != "ok":
        result["detail"] = f"age={age:.0f}s"
    return result


def check_soft_delete_indexes() -> dict:
    """Ensure partial unique indexes for soft-delete exist."""
    required = {
        "idx_tables_tenant_code_active": "tables",
        "idx_menu_items_tenant_sku_active": "menu_items",
    }
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename IN ('tables','menu_items')"
                )
            )
        defs = {row.indexname: row.indexdef for row in rows}
        missing = [name for name in required if name not in defs]
        invalid = [
            name
            for name in required
            if name in defs and "WHERE deleted_at IS NULL" not in defs[name]
        ]
        if missing or invalid:
            parts = []
            if missing:
                parts.append("missing=" + ",".join(missing))
            if invalid:
                parts.append("invalid=" + ",".join(invalid))
            return {
                "name": "soft_delete_indexes",
                "status": "fail",
                "detail": "; ".join(parts),
            }
        return {"name": "soft_delete_indexes", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "soft_delete_indexes", "status": "fail", "detail": str(exc)}


async def check_quotas() -> dict:
    """Verify quotas endpoint returns sane values."""
    tenant = os.getenv("PREFLIGHT_TENANT", "demo")
    try:
        from . import auth
        from .main import app

        class _User:
            role = "super_admin"

        try:
            app.dependency_overrides[auth.get_current_user] = (
                lambda token=None: _User()
            )
            async with httpx.AsyncClient(
                app=app, base_url="http://test", timeout=5
            ) as client:
                resp = await client.get(
                    f"/api/outlet/{tenant}/limits/usage",
                    headers={"X-Tenant-ID": tenant},
                )
        finally:
            app.dependency_overrides.pop(auth.get_current_user, None)
        if resp.status_code != 200:
            return {
                "name": "quotas",
                "status": "fail",
                "detail": f"http {resp.status_code}",
            }
        data = resp.json().get("data")
        if not isinstance(data, dict):
            return {"name": "quotas", "status": "fail", "detail": "malformed"}
        for metric, vals in data.items():
            used = vals.get("used")
            limit = vals.get("limit")
            if (used is not None and used < 0) or (limit is not None and limit < 0):
                return {
                    "name": "quotas",
                    "status": "fail",
                    "detail": f"negative {metric}",
                }
        return {"name": "quotas", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "quotas", "status": "fail", "detail": str(exc)}


async def check_webhook_metrics() -> dict:
    """Ensure webhook metrics expose breaker state."""
    try:
        from .main import app

        async with httpx.AsyncClient(app=app, base_url="http://test", timeout=5) as client:
            resp = await client.get("/metrics")
        if resp.status_code != 200:
            return {
                "name": "webhook_metrics",
                "status": "fail",
                "detail": f"http {resp.status_code}",
            }
        if "webhook_breaker_state" not in resp.text:
            return {
                "name": "webhook_metrics",
                "status": "fail",
                "detail": "missing webhook_breaker_state",
            }
        return {"name": "webhook_metrics", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "webhook_metrics", "status": "fail", "detail": str(exc)}


async def check_replica() -> dict:
    """Verify replica gauge and fallback health."""
    try:
        from .main import app
        from .db.replica import replica_session

        async with httpx.AsyncClient(app=app, base_url="http://test", timeout=5) as client:
            resp = await client.get("/metrics")
        if resp.status_code != 200:
            return {
                "name": "replica",
                "status": "fail",
                "detail": "metrics unreachable",
            }
        gauge_line = next(
            (line for line in resp.text.splitlines() if line.startswith("db_replica_healthy")),
            None,
        )
        if gauge_line is None:
            return {
                "name": "replica",
                "status": "fail",
                "detail": "gauge missing",
            }
        value = float(gauge_line.split()[-1])
        replica_url = os.getenv("READ_REPLICA_URL")
        if replica_url:
            if value >= 1:
                return {"name": "replica", "status": "ok"}
            return {"name": "replica", "status": "fail", "detail": "unhealthy"}
        # no replica configured - ensure fallback works
        try:
            async with replica_session() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - best effort
            return {
                "name": "replica",
                "status": "fail",
                "detail": f"fallback failed: {exc}",
            }
        return {"name": "replica", "status": "ok", "detail": "fallback"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "replica", "status": "fail", "detail": str(exc)}


@router.get("/api/admin/preflight")
async def preflight() -> dict:
    checks = [
        await check_db(),
        await check_redis(),
        check_migrations(),
        await check_storage(),
        check_webhooks(),
        await check_alertmanager(),
        check_backups(),
        check_soft_delete_indexes(),
        await check_quotas(),
        await check_webhook_metrics(),
        await check_replica(),
    ]
    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warn" for c in checks):
        overall = "warn"
    return {"status": overall, "checks": checks}

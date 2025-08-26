from __future__ import annotations

"""Operational preflight checklist endpoint."""

import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import APIRouter, UploadFile
from prometheus_client import generate_latest
from sqlalchemy import text

from .db import SessionLocal, engine
from .storage import storage
from .routes_metrics import db_replica_healthy

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
    try:
        if engine.dialect.name != "postgresql":
            return {
                "name": "soft_delete_indexes",
                "status": "warn",
                "detail": "postgres only",
            }
        expected = [
            "idx_tables_tenant_code_active",
            "idx_menu_items_tenant_sku_active",
        ]
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE indexname = ANY(:names)"
                ),
                {"names": expected},
            ).fetchall()
        found = {row[0]: row[1] for row in rows}
        missing = [name for name in expected if name not in found]
        invalid = [
            name
            for name, idx in found.items()
            if "WHERE deleted_at IS NULL" not in idx or "UNIQUE" not in idx
        ]
        if missing or invalid:
            detail_parts = []
            if missing:
                detail_parts.append(f"missing: {', '.join(missing)}")
            if invalid:
                detail_parts.append(f"invalid: {', '.join(invalid)}")
            return {
                "name": "soft_delete_indexes",
                "status": "fail",
                "detail": "; ".join(detail_parts),
            }
        return {"name": "soft_delete_indexes", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "soft_delete_indexes", "status": "fail", "detail": str(exc)}


async def check_quotas() -> dict:
    url = os.getenv("QUOTAS_URL")
    if not url:
        return {"name": "quotas", "status": "warn", "detail": "missing"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
        data = resp.json() if resp.content else None
        if resp.status_code != 200 or not isinstance(data, dict) or not data:
            return {
                "name": "quotas",
                "status": "fail",
                "detail": "invalid response",
            }
        return {"name": "quotas", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "quotas", "status": "fail", "detail": str(exc)}


def check_webhook_metrics() -> dict:
    try:
        metrics = generate_latest()
        if b"webhook_breaker_state" not in metrics:
            return {
                "name": "webhook_metrics",
                "status": "fail",
                "detail": "webhook_breaker_state missing",
            }
        return {"name": "webhook_metrics", "status": "ok"}
    except Exception as exc:  # pragma: no cover - best effort
        return {"name": "webhook_metrics", "status": "fail", "detail": str(exc)}


def check_replica_gauge() -> dict:
    try:
        value = db_replica_healthy._value.get()  # type: ignore[attr-defined]
        replica_url = os.getenv("READ_REPLICA_URL")
        if replica_url:
            if value == 1:
                return {"name": "replica", "status": "ok"}
            return {
                "name": "replica",
                "status": "fail",
                "detail": "unhealthy",
            }
        # no replica configured, falling back to primary
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
        check_webhook_metrics(),
        check_replica_gauge(),
    ]
    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warn" for c in checks):
        overall = "warn"
    return {"status": overall, "checks": checks}

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
    ]
    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warn" for c in checks):
        overall = "warn"
    return {"status": overall, "checks": checks}

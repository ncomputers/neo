"""Verify long-soft-deleted rows are purged and logged."""

import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore  # noqa: E402

from api.app.models_tenant import AuditTenant  # type: ignore  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _prepare(tmp_path, monkeypatch):
    tenant = "t1"
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )

    engine = get_engine(tenant)
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE tables (id INTEGER PRIMARY KEY, deleted_at DATETIME)")
        )
        await conn.execute(
            text(
                "CREATE TABLE menu_items (id INTEGER PRIMARY KEY, deleted_at DATETIME)"
            )
        )
        await conn.run_sync(AuditTenant.__table__.create)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    old_ts = datetime.utcnow() - timedelta(days=120)
    new_ts = datetime.utcnow() - timedelta(days=30)

    async with Session() as session:
        await session.execute(
            text("INSERT INTO tables (deleted_at) VALUES (:o), (:n), (NULL)"),
            {"o": old_ts, "n": new_ts},
        )
        await session.execute(
            text("INSERT INTO menu_items (deleted_at) VALUES (:o), (:n), (NULL)"),
            {"o": old_ts, "n": new_ts},
        )
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "purge_soft_deleted",
        ROOT / "scripts/purge_soft_deleted.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return tenant, Session, mod, engine


@pytest.mark.anyio
async def test_purge_soft_deleted(tmp_path, monkeypatch):
    tenant, Session, mod, engine = await _prepare(tmp_path, monkeypatch)
    await mod.purge(tenant, 90)

    async with Session() as session:
        table_count = (
            await session.execute(text("SELECT COUNT(*) FROM tables"))
        ).scalar()
        item_count = (
            await session.execute(text("SELECT COUNT(*) FROM menu_items"))
        ).scalar()
        audit = (
            await session.execute(text("SELECT action, meta FROM audit_tenant"))
        ).first()
        meta = json.loads(audit.meta) if isinstance(audit.meta, str) else audit.meta

    assert table_count == 2
    assert item_count == 2
    assert audit.action == "purge_soft_deleted"
    assert meta["tables"] == 1
    assert meta["menu_items"] == 1

    await engine.dispose()


@pytest.mark.anyio
async def test_purge_soft_deleted_dry_run(tmp_path, monkeypatch, capsys):
    tenant, Session, mod, engine = await _prepare(tmp_path, monkeypatch)
    await mod.purge(tenant, 90, dry_run=True)
    out = capsys.readouterr().out

    async with Session() as session:
        table_count = (
            await session.execute(text("SELECT COUNT(*) FROM tables"))
        ).scalar()
        item_count = (
            await session.execute(text("SELECT COUNT(*) FROM menu_items"))
        ).scalar()
        audit_count = (
            await session.execute(text("SELECT COUNT(*) FROM audit_tenant"))
        ).scalar()

    assert table_count == 3
    assert item_count == 3
    assert audit_count == 0
    assert "tables=1" in out
    assert "menu_items=1" in out

    await engine.dispose()

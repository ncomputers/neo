import asyncio
import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.models_tenant import AuditTenant  # noqa: E402
from api.app.db import SessionLocal as AuditSession  # noqa: E402


def _setup(tmp_path, monkeypatch):
    import api.app.auth as auth

    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())
    from api.app import routes_admin_privacy
    importlib.reload(routes_admin_privacy)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'tenant.db'}")

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE customers ("
                    "id INTEGER PRIMARY KEY, "
                    "name TEXT, "
                    "phone TEXT, "
                    "email TEXT, "
                    "created_at DATETIME)"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE invoices ("
                    "id INTEGER PRIMARY KEY, "
                    "name TEXT, "
                    "phone TEXT, "
                    "email TEXT, "
                    "created_at DATETIME)"
                )
            )
            await conn.commit()

    asyncio.run(_init())
    tenant_id = "t1"
    monkeypatch.setattr(routes_admin_privacy, "get_engine", lambda tid: engine)

    app = FastAPI()
    app.include_router(routes_admin_privacy.router)
    client = TestClient(app)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return client, tenant_id, Session


def test_dsar_export_and_delete(tmp_path, monkeypatch):
    client, tenant, Session = _setup(tmp_path, monkeypatch)

    async def seed() -> None:
        async with Session() as session:
            await session.execute(
                text(
                    "INSERT INTO customers (name, phone, email, created_at) "
                    "VALUES (:n,:p,:e,'2023-01-01')"
                ),
                {"n": "Alice", "p": "111", "e": "a@example.com"},
            )
            await session.execute(
                text(
                    "INSERT INTO invoices (name, phone, email, created_at) "
                    "VALUES (:n,:p,:e,'2023-01-02')"
                ),
                {"n": "Alice", "p": "111", "e": "a@example.com"},
            )
            await session.commit()

    asyncio.run(seed())

    with AuditSession() as s:
        s.query(AuditTenant).delete()
        s.commit()

    resp = client.post(
        f"/api/outlet/{tenant}/privacy/dsar/export", json={"phone": "111"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["customers"][0]["phone"] == "111"
    assert data["invoices"][0]["email"] == "a@example.com"

    with AuditSession() as s:
        row = s.query(AuditTenant).filter_by(action="dsar_export").first()
        assert row is not None
        assert row.meta["payload"]["phone"] == "***"

    resp = client.post(
        f"/api/outlet/{tenant}/privacy/dsar/delete",
        json={"phone": "111", "dry_run": True},
    )
    counts = resp.json()["data"]
    assert counts["customers"] == 1
    assert counts["invoices"] == 1

    async def check_exists() -> tuple[str | None, str | None, str | None]:
        async with Session() as session:
            row = (
                await session.execute(
                    text("SELECT name, phone, email FROM customers WHERE phone='111'")
                )
            ).first()
            return row

    assert asyncio.run(check_exists()) == ("Alice", "111", "a@example.com")

    resp = client.post(
        f"/api/outlet/{tenant}/privacy/dsar/delete", json={"phone": "111"}
    )
    assert resp.status_code == 200

    async def check_deleted() -> tuple[tuple | None, tuple | None]:
        async with Session() as session:
            cust = (
                await session.execute(
                    text("SELECT name, phone, email FROM customers")
                )
            ).first()
            inv = (
                await session.execute(text("SELECT name, phone, email FROM invoices"))
            ).first()
            return cust, inv

    cust, inv = asyncio.run(check_deleted())
    assert cust == (None, None, None)
    assert inv == (None, None, None)

    with AuditSession() as s:
        row = s.query(AuditTenant).filter_by(action="dsar_delete").first()
        assert row is not None
        assert row.meta["payload"]["phone"] == "***"

"""Verify PII anonymizer clears old fields and logs summary."""

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


@pytest.mark.anyio
async def test_anonymize_pii(tmp_path, monkeypatch):
    tenant = "t1"
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )

    engine = get_engine(tenant)
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
        await conn.run_sync(AuditTenant.__table__.create)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    old_ts = datetime.utcnow() - timedelta(days=40)
    new_ts = datetime.utcnow() - timedelta(days=5)

    async with Session() as session:
        await session.execute(
            text(
                "INSERT INTO customers (name, phone, email, created_at) "
                "VALUES (:n1,:p1,:e1,:o), (:n2,:p2,:e2,:n)"
            ),
            {
                "n1": "Old",
                "p1": "111",
                "e1": "old@example.com",
                "o": old_ts,
                "n2": "New",
                "p2": "222",
                "e2": "new@example.com",
                "n": new_ts,
            },
        )
        await session.execute(
            text(
                "INSERT INTO invoices (name, phone, email, created_at) "
                "VALUES (:n1,:p1,:e1,:o), (:n2,:p2,:e2,:n)"
            ),
            {
                "n1": "OldI",
                "p1": "333",
                "e1": "oldi@example.com",
                "o": old_ts,
                "n2": "NewI",
                "p2": "444",
                "e2": "newi@example.com",
                "n": new_ts,
            },
        )
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "anonymize_pii", ROOT / "scripts/anonymize_pii.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    await mod.anonymize(tenant, 30)

    async with Session() as session:
        cust_rows = (
            await session.execute(
                text("SELECT name, phone, email FROM customers ORDER BY id")
            )
        ).all()
        inv_rows = (
            await session.execute(
                text("SELECT name, phone, email FROM invoices ORDER BY id")
            )
        ).all()
        audit = (
            await session.execute(text("SELECT actor, action, meta FROM audit_tenant"))
        ).first()
        meta = json.loads(audit.meta) if isinstance(audit.meta, str) else audit.meta

    assert cust_rows[0] == (None, None, None)
    assert inv_rows[0] == (None, None, None)
    assert cust_rows[1] == ("New", "222", "new@example.com")
    assert inv_rows[1] == ("NewI", "444", "newi@example.com")
    assert audit.action == "anonymize_pii"
    assert meta["customers"] == 1
    assert meta["invoices"] == 1

    await engine.dispose()

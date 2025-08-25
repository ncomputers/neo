from __future__ import annotations

import importlib.util
import pathlib
import sys
import uuid

import pytest
from sqlalchemy import select

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from api.app.db.tenant import (  # type: ignore  # noqa: E402
    get_engine,
    get_tenant_session,
)
from api.app.models_tenant import Base, Table  # type: ignore  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_regen_qr_rotates_token(tmp_path, monkeypatch):
    tenant = "demo"
    template = f"sqlite+aiosqlite:///{tmp_path}/{{tenant_id}}.db"
    monkeypatch.setenv("POSTGRES_TENANT_DSN_TEMPLATE", template)

    engine = get_engine(tenant)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_tenant_session(tenant) as session:
        table = Table(
            tenant_id=uuid.uuid4(),
            name="Table 1",
            code="T-001",
            qr_token="old",
        )
        session.add(table)
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "tenant_qr_tools", ROOT / "scripts" / "tenant_qr_tools.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    info = await mod.regen_qr(tenant, "T-001")
    new_token = info["qr_token"]
    assert new_token != "old"

    async with get_tenant_session(tenant) as session:
        old = await session.scalar(select(Table).where(Table.qr_token == "old"))
        new = await session.scalar(select(Table).where(Table.qr_token == new_token))
        assert old is None
        assert new is not None

    await engine.dispose()

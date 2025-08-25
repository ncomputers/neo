import pathlib
import sys
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from api.app.auth import create_access_token  # noqa: E402
from api.app.db.tenant import get_engine, get_tenant_session  # noqa: E402
from api.app.models_tenant import Base, Table, AuditTenant  # noqa: E402
from api.app.routes_tables_qr_rotate import router  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:  # pragma: no cover - required by pytest-anyio
    return "asyncio"


@pytest.mark.anyio
async def test_rotate_endpoint_invalidates_old_token(tmp_path, monkeypatch):
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

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/outlet/{tenant}/tables/T-001/qr/rotate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    deeplink = data["deeplink"]
    assert deeplink.startswith("https://example.com/")
    assert data["qr_png_data_url"].startswith("data:image/png;base64,")

    async with get_tenant_session(tenant) as session:
        old = await session.scalar(select(Table).where(Table.qr_token == "old"))
        table = await session.scalar(select(Table).where(Table.code == "T-001"))
        assert old is None
        assert table is not None and table.qr_token != "old"
        assert deeplink.endswith(table.qr_token)

    with SessionLocal() as session:
        row = session.query(AuditTenant).filter_by(action="qr_rotate").first()
        assert row is not None

    await engine.dispose()

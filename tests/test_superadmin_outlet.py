from __future__ import annotations

import asyncio
import importlib
import os
import uuid

from fastapi.testclient import TestClient


def test_outlet_creates_master_row(tmp_path, monkeypatch) -> None:
    os.environ["ADMIN_API_ENABLED"] = "true"
    os.environ["POSTGRES_MASTER_URL"] = (
        f"sqlite+aiosqlite:///{tmp_path/'master.db'}"
    )

    import api.app.db.master as master
    importlib.reload(master)
    import api.app.main as app_main
    importlib.reload(app_main)
    app = app_main.app

    class DummyRedis:
        async def sismember(self, *args, **kwargs):
            return False

        async def incr(self, *args, **kwargs):
            return 0

        async def sadd(self, *args, **kwargs):
            return 0

    app.state.redis = DummyRedis()

    monkeypatch.setattr(
        "api.app.routes_superadmin.subprocess.run", lambda *a, **k: None
    )

    from api.app.models_master import Base, Tenant

    async def _init() -> None:
        engine = master.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    client = TestClient(app)
    resp = client.post(
        "/api/super/outlet",
        json={"name": "Cafe Test", "tz": "UTC", "plan_tables": 4},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tz"] == "UTC"
    assert data["licensed_tables"] == 4
    tenant_id = uuid.UUID(data["tenant_id"])

    async def _fetch():
        async with master.get_session() as session:
            return await session.get(Tenant, tenant_id)

    tenant = asyncio.run(_fetch())
    assert tenant is not None
    assert tenant.name == "Cafe Test"
    assert tenant.inv_prefix == data["inv_prefix"]
    assert tenant.timezone == "UTC"
    assert tenant.licensed_tables == 4
    assert tenant.status == "active"

    # restore modules to avoid side effects on other tests
    importlib.reload(app_main)
    importlib.reload(master)
    os.environ.pop("ADMIN_API_ENABLED", None)
    os.environ.pop("POSTGRES_MASTER_URL", None)


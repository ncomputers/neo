import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.models_tenant import Base


def test_bill_enqueue_outbox(tmp_path, monkeypatch):
    import importlib
    import api.app.auth as auth
    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())
    from api.app import routes_alerts, routes_guest_bill
    from api.app.services import notifications
    importlib.reload(routes_alerts)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'tenant.db'}")

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    tenant_id = "t1"

    monkeypatch.setattr(routes_alerts, "get_engine", lambda tid: engine)
    monkeypatch.setattr(notifications, "get_engine", lambda tid: engine)
    async def _gen_invoice(**kwargs):
        return 1
    monkeypatch.setattr(routes_guest_bill.invoices_repo_sql, "generate_invoice", _gen_invoice)
    monkeypatch.setattr(routes_guest_bill.billing_service, "compute_bill", lambda *a, **k: {})

    app = FastAPI()
    app.include_router(routes_alerts.router)
    app.include_router(routes_guest_bill.router)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @asynccontextmanager
    async def _session_override():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[routes_guest_bill.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[routes_guest_bill.get_tenant_session] = _session_override

    client = TestClient(app)

    resp = client.post(
        f"/api/outlet/{tenant_id}/alerts/rules",
        json={
            "event": "bill.generated",
            "channel": "webhook",
            "target": "https://example.com/hook",
            "enabled": True,
        },
    )
    assert resp.status_code == 200

    resp = client.post("/g/x/bill")
    assert resp.status_code == 200

    resp = client.get(
        f"/api/outlet/{tenant_id}/alerts/outbox", params={"status": "queued"}
    )
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["event"] == "bill.generated"

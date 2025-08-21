import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.models_tenant import Base, NotificationOutbox


def test_bill_enqueue_outbox(tmp_path, monkeypatch):
    import importlib
    import api.app.auth as auth
    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())
    from api.app import routes_admin_alerts
    from api.app.services import notifications
    importlib.reload(routes_admin_alerts)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'tenant.db'}")

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    tenant_id = "t1"

    monkeypatch.setattr(routes_admin_alerts, "get_engine", lambda tid: engine)
    monkeypatch.setattr(notifications, "get_engine", lambda tid: engine)

    app = FastAPI()
    app.include_router(routes_admin_alerts.router)

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

    asyncio.run(notifications.enqueue(tenant_id, "bill.generated", {"x": 1}))

    async def _fetch() -> list[NotificationOutbox]:
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Session() as session:
            result = await session.execute(select(NotificationOutbox))
            return result.scalars().all()

    rows = asyncio.run(_fetch())
    assert len(rows) == 1
    assert rows[0].event == "bill.generated"
    assert rows[0].status == "queued"

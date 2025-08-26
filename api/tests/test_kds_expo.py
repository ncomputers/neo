import datetime
import pathlib
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import api.app.db as app_db  # noqa: E402
import api.app.domain as app_domain  # noqa: E402
import api.app.models_tenant as app_models_tenant  # noqa: E402
import api.app.repos_sqlalchemy as app_repos_sqlalchemy  # noqa: E402
import api.app.utils as app_utils  # noqa: E402

sys.modules.setdefault("db", app_db)
sys.modules.setdefault("domain", app_domain)
sys.modules.setdefault("models_tenant", app_models_tenant)
sys.modules.setdefault("repos_sqlalchemy", app_repos_sqlalchemy)
sys.modules.setdefault("utils", app_utils)

from api.app import routes_kds_expo  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.domain import OrderStatus  # noqa: E402
from api.app.models_tenant import AuditTenant  # noqa: E402

app = FastAPI()
app.include_router(routes_kds_expo.router)
client = TestClient(app)


class DummySession:
    def __init__(self):
        self.status = OrderStatus.READY
        self.ready_at = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(seconds=30)

    async def execute(self, query):
        name = getattr(query, "__visit_name__", "")
        if name == "select":
            return SimpleNamespace(
                all=lambda: [
                    SimpleNamespace(
                        id=1,
                        code="T1",
                        ready_at=self.ready_at,
                        allergens=["nuts"],
                    )
                ],
                scalar_one_or_none=lambda: self.status,
                first=lambda: SimpleNamespace(status=self.status),
            )
        elif name == "update":
            self.status = OrderStatus.SERVED
            return SimpleNamespace(rowcount=1)
        return SimpleNamespace()

    async def commit(self):
        return None


@asynccontextmanager
async def fake_session(_tenant_id: str):
    yield DummySession()


def test_ready_to_picked_flow(monkeypatch):
    monkeypatch.setattr(routes_kds_expo, "_session", fake_session)
    with SessionLocal() as s:
        s.query(AuditTenant).delete()
        s.commit()

    resp = client.get("/api/outlet/demo/kds/expo")
    assert resp.status_code == 200
    data = resp.json()["data"]["orders"][0]
    assert data["table"] == "T1"
    assert data["allergen_badges"] == ["nuts"]

    resp = client.post("/api/outlet/demo/kds/expo/1/picked")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == OrderStatus.SERVED.value

    with SessionLocal() as s:
        row = s.query(AuditTenant).filter_by(action="expo.picked").first()
        assert row is not None
        assert row.meta["target"]["order_id"] == "1"

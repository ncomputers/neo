import os
import pathlib
import sys
import types
import uuid

import fakeredis.aioredis
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

# stub modules required by imported code
_webhooks = types.ModuleType("routes_webhooks")
_webhooks.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhooks", _webhooks)
_webhook_tools = types.ModuleType("routes_webhook_tools")
_webhook_tools.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhook_tools", _webhook_tools)

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://u:p@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from api.app.auth import create_access_token  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_tenant import Table  # noqa: E402
from api.app.routes_tables_map import router as tables_router  # noqa: E402

app = FastAPI()
app.include_router(tables_router)
app.state.redis = fakeredis.aioredis.FakeRedis()
client = TestClient(app)


def test_soft_delete_and_restore_table():
    table_code = "T3"
    table_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(
            Table(
                id=table_id,
                tenant_id=uuid.uuid4(),
                name="T3",
                code=table_code,
                state="AVAILABLE",
            )
        )
        session.commit()

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}

    assert any(
        t["code"] == table_code
        for t in client.get("/api/outlet/demo/tables/map").json()["data"]
    )

    assert (
        client.patch(
            f"/api/outlet/demo/tables/{table_code}/delete", headers=headers
        ).status_code
        == 200
    )
    assert all(
        t["code"] != table_code
        for t in client.get("/api/outlet/demo/tables/map").json()["data"]
    )
    assert any(
        t["code"] == table_code
        for t in client.get("/api/outlet/demo/tables/map?include_deleted=true").json()[
            "data"
        ]
    )
    assert (
        client.post(
            f"/api/outlet/demo/tables/{table_code}/restore", headers=headers
        ).status_code
        == 200
    )
    assert any(
        t["code"] == table_code
        for t in client.get("/api/outlet/demo/tables/map").json()["data"]
    )

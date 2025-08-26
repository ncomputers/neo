
import os
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
import api.app.menu as menu

# provide minimal menu router for main app import
menu.router = APIRouter()
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgres://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
from api.app.main import app
from api.app.repos_sqlalchemy import orders_repo_sql


@pytest.fixture
def client(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis()
    app.state.redis = fake

    async def fake_list_active(session, tenant_id):
        return []

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class _Dummy:
            pass
        yield _Dummy()

    monkeypatch.setattr(orders_repo_sql, "list_active", fake_list_active)
    monkeypatch.setattr("api.app.routes_kds._session", fake_session)
    return TestClient(app), fake


def test_printer_offline_banner(client):
    client, redis = client
    # No heartbeat set -> stale
    import asyncio

    asyncio.run(redis.lpush("print:q:demo", "m1"))
    resp = client.get("/api/outlet/demo/kds/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["printer_stale"] is True
    assert body["data"]["retry_queue"] == 1

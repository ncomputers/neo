from __future__ import annotations

import asyncio
import datetime

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_metrics import router as metrics_router
from api.app.routes_print_bridge import router as print_router


def test_printer_status_and_metrics():
    app = FastAPI()
    app.include_router(print_router)
    app.include_router(metrics_router)
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis

    tenant = "demo"
    stale_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=5
    )

    async def seed() -> None:
        await redis.set(f"print:hb:{tenant}", stale_time.isoformat())
        await redis.rpush(f"print:retry:{tenant}", "job1")

    asyncio.run(seed())

    client = TestClient(app)
    resp = client.get(f"/api/outlet/{tenant}/print/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale"] is True
    assert data["queue"] == 1

    body = client.get("/metrics").text
    assert "printer_retry_queue 1.0" in body
    assert "printer_retry_queue_age 0.0" in body

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
    import asyncio, json
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = (now - datetime.timedelta(seconds=90)).isoformat()
    asyncio.run(redis.lpush("print:q:demo", json.dumps({"ts": ts, "m": 1})))
    resp = client.get("/api/outlet/demo/kds/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["printer_stale"] is True
    assert body["data"]["retry_queue"] == 1
    assert body["data"]["retry_queue_age"] >= 90
    metrics_body = client.get("/metrics").text
    assert "printer_retry_queue 1.0" in metrics_body
    assert "printer_retry_queue_age" in metrics_body

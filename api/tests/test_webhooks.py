import asyncio
import json
import pathlib
import sys
from contextlib import asynccontextmanager

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import os
import types
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "*")
sys.modules.setdefault("PIL", types.ModuleType("PIL"))
sys.modules.setdefault("PIL.Image", types.ModuleType("Image"))
sys.modules.setdefault("PIL.ImageOps", types.ModuleType("ImageOps"))

import fakeredis.aioredis
import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from api.app.auth import create_access_token
from api.app.main import app
from api.app import routes_webhooks
from api.app.models_tenant import NotificationOutbox
from api.app.utils.scrub import scrub_payload

app.state.redis = fakeredis.aioredis.FakeRedis()


def test_scrub_payload_removes_secrets():
    data = {"token": "abc", "nested": {"password": "p", "ok": 1}}
    scrubbed = scrub_payload(data)
    assert scrubbed["token"] == "***"
    assert scrubbed["nested"]["password"] == "***"
    assert scrubbed["nested"]["ok"] == 1


def test_webhook_test_endpoint(monkeypatch):
    called = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, content=None, headers=None):
            called["url"] = url
            called["body"] = content
            called["headers"] = headers
            return httpx.Response(200)

    class FakeHttpx:
        AsyncClient = DummyClient

    monkeypatch.setattr(routes_webhooks, "httpx", FakeHttpx)
    monkeypatch.setattr(routes_webhooks, "is_allowed_url", lambda url: True)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            app.state.redis = fakeredis.aioredis.FakeRedis()
            resp = await client.post(
                "/api/outlet/t1/webhooks/test",
                json={"url": "http://example.com/hook", "event": "ping"},
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    body = json.loads(called["body"].decode())
    assert body["event"] == "ping"


def test_webhook_replay(monkeypatch):
    existing = NotificationOutbox(
        event="foo",
        payload={"a": 1},
        channel="webhook",
        target="http://example.com",
        status="delivered",
    )

    class DummySession:
        def __init__(self):
            self.added = None

        async def get(self, model, item_id):
            return existing

        def add(self, obj):
            self.added = obj

        async def commit(self):
            pass

    holder = {}

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        session = DummySession()
        holder["session"] = session
        yield session

    monkeypatch.setattr(routes_webhooks, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            app.state.redis = fakeredis.aioredis.FakeRedis()
            return await client.post(
                "/api/outlet/t1/webhooks/1/replay",
                headers={"Authorization": f"Bearer {token}"},
            )

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    session = holder["session"]
    assert isinstance(session.added, NotificationOutbox)
    assert session.added.event == existing.event
    assert session.added.status == "queued"

import asyncio
import json
import pathlib
import sys

import pytest
from fakeredis import aioredis
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.requests import Request

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.main import app, settings, ws_connections
from api.app import routes_tables_sse


client = TestClient(app)


def _setup_redis(monkeypatch):
    fake = aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)
    monkeypatch.setattr("api.app.routes_tables_sse.redis_client", fake, raising=False)
    from api.app.main import app as main_app
    main_app.state.redis = fake
    return fake


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def query(self, model):
        return self

    def all(self):
        return []


def test_ws_conn_limit(monkeypatch):
    _setup_redis(monkeypatch)
    monkeypatch.setattr(settings, "max_conn_per_ip", 1)
    url = "/tables/T1/ws"
    with client.websocket_connect(url):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url):
                pass
    ws_connections.clear()


def test_ws_backpressure(monkeypatch):
    fake = _setup_redis(monkeypatch)
    monkeypatch.setattr(settings, "max_conn_per_ip", 2)

    original_send = WebSocket.send_json

    async def slow_send(self, data):
        await asyncio.sleep(0.01)
        await original_send(self, data)

    monkeypatch.setattr(WebSocket, "send_json", slow_send)

    url = "/tables/T2/ws"
    with client.websocket_connect(url) as ws:
        async def publish():
            for i in range(101):
                await fake.publish("rt:update:T2", json.dumps({"i": i}))
        asyncio.run(publish())
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    ws_connections.clear()


def test_sse_conn_limit(monkeypatch):
    _setup_redis(monkeypatch)
    monkeypatch.setattr(routes_tables_sse, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(routes_tables_sse.settings, "max_conn_per_ip", 1)
    scope = {"type": "http", "client": ("1.2.3.4", 0), "headers": []}
    req = Request(scope)
    # first connection
    asyncio.run(routes_tables_sse.stream_table_map("demo", req, None))
    with pytest.raises(HTTPException):
        asyncio.run(routes_tables_sse.stream_table_map("demo", req, None))
    routes_tables_sse.sse_connections.clear()

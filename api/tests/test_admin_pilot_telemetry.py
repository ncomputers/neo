import os
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import types

from fastapi import FastAPI

from api.app import routes_admin_pilot  # noqa: E402
from api.app.routes_metrics import orders_created_total  # noqa: E402

sys.modules.setdefault("api.app.main", types.SimpleNamespace(prep_trackers={}))
app = FastAPI()
app.include_router(routes_admin_pilot.router)


def setup_function() -> None:
    routes_admin_pilot._CACHE["ts"] = 0.0
    routes_admin_pilot._CACHE["data"] = None
    routes_admin_pilot._LAST_ORDERS_TOTAL = None
    routes_admin_pilot._LAST_ORDERS_TS = None
    orders_created_total._value.set(0)  # type: ignore[attr-defined]
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_telemetry_shape():
    client = TestClient(app)
    resp = client.get("/api/admin/pilot/telemetry")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {
        "orders_per_min",
        "avg_prep",
        "breaker_open_pct",
        "kot_queue_age",
        "latency_p95_ms",
        "error_rate",
    } == set(data.keys())


def test_telemetry_cache(monkeypatch):
    from api.app import routes_admin_pilot

    class DummyTime:
        def __init__(self):
            self.now = 0.0

        def time(self):
            return self.now

    dummy = DummyTime()
    monkeypatch.setattr(routes_admin_pilot.time, "time", dummy.time)

    client = TestClient(app)
    resp1 = client.get("/api/admin/pilot/telemetry")
    data1 = resp1.json()["data"]

    orders_created_total.inc(10)
    dummy.now = 30
    resp2 = client.get("/api/admin/pilot/telemetry")
    assert resp2.json()["data"] == data1

    dummy.now = 100
    orders_created_total.inc(5)
    resp3 = client.get("/api/admin/pilot/telemetry")
    data3 = resp3.json()["data"]
    assert data3["orders_per_min"] != data1["orders_per_min"]

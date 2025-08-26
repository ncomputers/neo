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

import time
import types

from fastapi import FastAPI

from api.app import routes_pilot_telemetry  # noqa: E402
from api.app.routes_metrics import (  # noqa: E402
    http_errors_total,
    http_requests_total,
    orders_created_total,
    sse_clients_gauge,
)

sys.modules.setdefault("api.app.main", types.SimpleNamespace(prep_trackers={}))
app = FastAPI()
app.include_router(routes_pilot_telemetry.router)


def setup_function() -> None:
    routes_pilot_telemetry._CACHE["ts"] = 0.0
    routes_pilot_telemetry._CACHE["data"] = None
    routes_pilot_telemetry._LAST_ORDERS_TOTAL = None
    routes_pilot_telemetry._LAST_ORDERS_TS = None
    routes_pilot_telemetry._ERROR_SAMPLES.clear()
    orders_created_total._value.set(0)  # type: ignore[attr-defined]
    http_requests_total._metrics.clear()  # type: ignore[attr-defined]
    http_errors_total._metrics.clear()  # type: ignore[attr-defined]
    sse_clients_gauge.set(0)
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_telemetry_shape_and_ranges():
    client = TestClient(app)
    resp = client.get("/api/admin/pilot/telemetry")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {
        "orders_per_min",
        "avg_prep_s",
        "kot_queue_oldest_s",
        "p95_latency_ms",
        "error_rate_5m",
        "webhook_breaker_open_pct",
        "sse_clients",
        "timestamp",
    } == set(data.keys())
    assert data["orders_per_min"] >= 0
    assert data["avg_prep_s"] >= 0
    assert data["kot_queue_oldest_s"] >= 0
    assert data["p95_latency_ms"] >= 0
    assert 0 <= data["error_rate_5m"] <= 1
    assert 0 <= data["webhook_breaker_open_pct"] <= 100
    assert data["sse_clients"] >= 0
    assert abs(data["timestamp"] - int(time.time())) <= 1

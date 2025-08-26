import os
import pathlib
import sys
import types

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

sys.modules.setdefault("api.app.routes_admin_pilot", types.SimpleNamespace(router=None))
sys.modules.setdefault("api.app.routes_admin_print", types.SimpleNamespace(router=None))

import pytest
from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app
from api.app import flags as flags_module
from api.app.exp import ab_allocator
from api.app.routes_metrics import ab_exposures_total, ab_conversions_total


def _client(monkeypatch):
    monkeypatch.setattr(flags_module, "get", lambda name, tenant=None: True)
    class Dummy:
        ab_tests = {"MENU_COPY_V1": {"control": 1, "treat": 1}}
    monkeypatch.setattr(ab_allocator, "get_settings", lambda: Dummy())
    app.state.redis = fakeredis.aioredis.FakeRedis()
    return TestClient(app)


def test_report_and_lift(monkeypatch):
    client = _client(monkeypatch)
    device_id = "abc"
    assert ab_allocator.get_variant(device_id, "MENU_COPY_V1") == ab_allocator.get_variant(
        device_id, "MENU_COPY_V1"
    )

    ab_exposures_total.labels(experiment="MENU_COPY_V1", variant="control").inc(100)
    ab_conversions_total.labels(experiment="MENU_COPY_V1", variant="control").inc(10)
    ab_exposures_total.labels(experiment="MENU_COPY_V1", variant="treat").inc(80)
    ab_conversions_total.labels(experiment="MENU_COPY_V1", variant="treat").inc(16)
    ab_conversions_total.labels(experiment="MENU_COPY_V1", variant="ghost").inc(1)

    resp = client.get(
        "/exp/ab/report",
        params={"experiment": "MENU_COPY_V1", "from": "2023-01-01", "to": "2023-01-31"},
    )
    assert resp.status_code == 200
    stats = {s["name"]: s for s in resp.json()["variant_stats"]}
    control_rate = stats["control"]["conv_rate"]
    treat_rate = stats["treat"]["conv_rate"]
    assert stats["treat"]["lift_vs_control"] == pytest.approx(
        treat_rate / control_rate - 1
    )
    assert stats["ghost"]["conv_rate"] == 0

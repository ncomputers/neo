from __future__ import annotations

import os
import sys
import types
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from prometheus_client import registry

import api.app.routes_analytics_outlets as routes_analytics_outlets

sys.modules.setdefault("api.app.routes_admin_pilot", types.SimpleNamespace(router=None))
sys.modules.setdefault("api.app.routes_admin_print", types.SimpleNamespace(router=None))

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)
os.environ.setdefault("DEFAULT_TZ", "UTC")

from api.app.main import app


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    async def scalar(self, stmt):
        text = str(stmt).lower()
        if "status" in text:
            return 1  # cancelled orders per tenant
        if "count" in text:
            return 2  # total orders per tenant
        if "sum" in text:
            return 100.0  # sales per tenant
        return None

    async def execute(self, stmt):
        text = str(stmt).lower()
        if "name_snapshot" in text:
            return FakeResult([("Veg Item", 2)])
        # accepted and ready times
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc)
        return FakeResult([(start, end)])


@asynccontextmanager
async def fake_session(tid):
    yield FakeSession()


@pytest.fixture(autouse=True)
def patch_deps(monkeypatch):
    registry.REGISTRY = registry.CollectorRegistry()
    monkeypatch.setattr(routes_analytics_outlets, "_session", fake_session)

    async def _get(ids):
        return {tid: {"name": tid, "tz": "UTC"} for tid in ids}

    monkeypatch.setattr(routes_analytics_outlets, "_get_tenants_info", _get)


@pytest.fixture
def client():
    return TestClient(app)


def test_valid_range_returns_metrics(client):
    ids = "t1,t2"
    resp = client.get(
        "/api/analytics/outlets",
        params={"ids": ids, "from": "2024-01-01", "to": "2024-01-02"},
        headers={"x-tenant-ids": ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders"] == 4
    assert data["sales"] == 200.0
    assert data["voids_pct"] == 50.0


def test_invalid_range(client):
    ids = "t1,t2"
    resp = client.get(
        "/api/analytics/outlets",
        params={"ids": ids, "from": "2024-01-02", "to": "2024-01-01"},
        headers={"x-tenant-ids": ids},
    )
    assert resp.status_code == 400


def test_ids_outside_scope(client):
    resp = client.get(
        "/api/analytics/outlets",
        params={"ids": "t1,x", "from": "2024-01-01", "to": "2024-01-02"},
        headers={"x-tenant-ids": "t1"},
    )
    assert resp.status_code == 403


def test_csv_format(client):
    ids = "t1,t2"
    resp = client.get(
        "/api/analytics/outlets",
        params={"ids": ids, "from": "2024-01-01", "to": "2024-01-02", "format": "csv"},
        headers={"x-tenant-ids": ids},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0].split(",") == [
        "outlet_id",
        "orders",
        "sales",
        "aov",
        "median_prep",
        "voids_pct",
    ]
    assert len(lines) == 3

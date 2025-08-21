import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app.deps import flags as flag_deps


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_hotel_flag_blocks_routes(client, monkeypatch):
    async def fake_can_use(tenant_id, flag):
        return False
    monkeypatch.setattr(flag_deps, "can_use", fake_can_use)
    headers = {"X-Tenant-ID": "demo"}
    resp = client.get("/h/ROOM1/menu", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["message"] == "DISABLED"


def test_counter_flag_blocks_routes(client, monkeypatch):
    async def fake_can_use(tenant_id, flag):
        return False
    monkeypatch.setattr(flag_deps, "can_use", fake_can_use)
    headers = {"X-Tenant-ID": "demo"}
    resp = client.get("/c/COUNTER1/menu", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["message"] == "DISABLED"

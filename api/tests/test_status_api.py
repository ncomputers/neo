import os
import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
os.environ.setdefault("POSTGRES_MASTER_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost")
from api.app.main import app  # noqa: E402


def test_status_json_endpoint():
    client = TestClient(app)
    resp = client.get("/status.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "api"
    assert "version" in data
    assert "db" in data
    assert "queue" in data
    assert "time" in data


def test_status_deps_endpoint():
    client = TestClient(app)
    resp = client.get("/status/deps")
    assert resp.status_code == 200
    data = resp.json()
    assert "webhooks" in data

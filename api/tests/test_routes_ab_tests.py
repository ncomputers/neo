import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app
from api.app import flags as flags_module
from api.app.exp import ab_allocator
from api.app.auth import authenticate_user


def _client(monkeypatch, flag_value: bool, variants: dict | None = None) -> TestClient:
    monkeypatch.setattr(flags_module, "get", lambda name, tenant=None: flag_value)
    if variants is not None:
        class Dummy:
            ab_tests = variants
        monkeypatch.setattr(ab_allocator, "get_settings", lambda: Dummy())
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.dependency_overrides[authenticate_user] = lambda: None
    return TestClient(app)


def test_returns_control_when_flag_disabled(monkeypatch):
    client = _client(monkeypatch, False)
    resp = client.get("/api/ab/sample?device_id=abc")
    assert resp.status_code == 200
    assert resp.json() == {"variant": "control"}


def test_deterministic_variant_when_enabled(monkeypatch):
    variants = {"sample": {"control": 1, "treat": 1}}
    client = _client(monkeypatch, True, variants)
    expected = ab_allocator.allocate("abc", "sample", variants["sample"])
    resp = client.get("/api/ab/sample?device_id=abc")
    assert resp.status_code == 200
    assert resp.json() == {"variant": expected}

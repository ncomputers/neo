import importlib
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def test_allowed_origins_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    from api.app import main as app_main
    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    client = TestClient(app_main.app)
    resp_ok = client.get("/ready", headers={"Origin": "https://allowed.com"})
    assert resp_ok.headers.get("access-control-allow-origin") == "https://allowed.com"

    resp_block = client.get("/ready", headers={"Origin": "https://bad.com"})
    assert "access-control-allow-origin" not in resp_block.headers

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    importlib.reload(app_main)

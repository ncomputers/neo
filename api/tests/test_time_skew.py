import os
import pathlib
import sys
from datetime import datetime, timezone

import fakeredis.aioredis
from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.main import app  # noqa: E402


def test_time_skew_returns_epoch():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app)
    resp = client.get("/time/skew")
    assert resp.status_code == 200
    data = resp.json()
    assert "epoch" in data
    now = int(datetime.now(timezone.utc).timestamp())
    assert abs(data["epoch"] - now) <= 5

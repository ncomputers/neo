import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.main import app  # noqa: E402


def test_version_fields_present():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app)
    resp = client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert {"sha", "built_at", "env"} <= data.keys()
    assert data["env"] in {"prod", "staging", "dev"}

import os
import pathlib
import sys
from datetime import datetime

from fastapi.testclient import TestClient
import fakeredis.aioredis
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "*")

from api.app import main as app_main  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402

app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def test_create_sandbox_tenant():
    client = TestClient(app)
    resp = client.post("/api/admin/tenant/sandbox", headers=_admin_headers())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "tenant_id" in data
    expires = datetime.fromisoformat(data["expires_at"])
    delta = expires - datetime.utcnow()
    assert 6 <= delta.days <= 7

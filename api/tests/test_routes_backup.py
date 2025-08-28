import pathlib
import sys
import os
import asyncio
import subprocess

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from api.app.main import app

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def _token(username: str, password: str) -> str:
    resp = client.post(
        "/login/email", json={"username": username, "password": password}
    )
    return resp.json()["data"]["access_token"]


def test_backup_requires_super_admin(monkeypatch):
    async def fake_to_thread(func, *args, **kwargs):
        return None

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)

    admin_token = _token("admin@example.com", "adminpass")
    resp = client.post(
        "/api/outlet/demo/backup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    owner_token = _token("owner@example.com", "ownerpass")
    resp = client.post(
        "/api/outlet/demo/backup",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 403

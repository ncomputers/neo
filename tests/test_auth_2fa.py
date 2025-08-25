from __future__ import annotations

import hashlib
import importlib

from fastapi.testclient import TestClient

from api.app.auth import create_access_token
from api.app.db import SessionLocal
from api.app.models_master import TwoFactorBackupCode, TwoFactorSecret
from api.app.routes_auth_2fa import _totp_now
from tests.conftest import DummyRedis


def _client() -> TestClient:
    import api.app.main as app_main

    importlib.reload(app_main)
    app = app_main.app
    app.state.redis = DummyRedis()
    return TestClient(app)


def test_two_factor_flow():
    client = _client()
    token = create_access_token({"sub": "admin@example.com", "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/auth/2fa/setup", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    secret = data["secret"]

    code = _totp_now(secret)
    resp = client.post("/auth/2fa/enable", json={"code": code}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/auth/2fa/backup", headers=headers)
    backup_codes = resp.json()["data"]["codes"]
    assert len(backup_codes) == 10

    code = _totp_now(secret)
    resp = client.post("/auth/2fa/verify", json={"code": code}, headers=headers)
    assert resp.status_code == 200

    backup = backup_codes[0]
    resp = client.post("/auth/2fa/verify", json={"code": backup}, headers=headers)
    assert resp.status_code == 200

    with SessionLocal() as db:
        entry = (
            db.query(TwoFactorBackupCode)
            .filter_by(
                user="admin@example.com",
                code_hash=hashlib.sha256(backup.encode()).hexdigest(),
            )
            .first()
        )
        assert entry and entry.used_at is not None

    code = _totp_now(secret)
    resp = client.post("/auth/2fa/disable", json={"code": code}, headers=headers)
    assert resp.status_code == 200

    with SessionLocal() as db:
        assert not db.query(TwoFactorSecret).filter_by(user="admin@example.com").count()

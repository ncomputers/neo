import pathlib
import sys
import subprocess

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from api.app.main import app
from api.app.db.master import SessionLocal
from api.app.models import Tenant

client = TestClient(app, raise_server_exceptions=False)


def setup_function():
    with SessionLocal() as session:
        session.query(Tenant).delete()
        session.commit()


def test_provision_success(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    resp = client.post(
        "/api/super/tenants", json={"name": "Demo", "domain": "demo.local"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "tenant_id" in data
    with SessionLocal() as session:
        assert session.query(Tenant).count() == 1


def test_provision_migration_failure(monkeypatch):
    def bad_run(*a, **k):
        raise subprocess.CalledProcessError(1, "alembic")

    monkeypatch.setattr(subprocess, "run", bad_run)
    resp = client.post(
        "/api/super/tenants", json={"name": "Demo", "domain": "demo.local"}
    )
    assert resp.status_code == 500

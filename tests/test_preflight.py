import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app.main import app
import api.app.routes_preflight as routes_preflight


async def ok_async(name="x"):
    return {"name": name, "status": "ok"}


def ok_sync(name="x"):
    return {"name": name, "status": "ok"}


def fail_sync(name="x"):
    return {"name": name, "status": "fail"}


async def fail_async(name="x"):
    return {"name": name, "status": "fail"}


def warn_sync(name="x"):
    return {"name": name, "status": "warn"}


async def warn_async(name="x"):
    return {"name": name, "status": "warn"}


def _patch_all(monkeypatch, mapping):
    for fname, func in mapping.items():
        monkeypatch.setattr(routes_preflight, fname, func)


def test_preflight_ok(monkeypatch):
    _patch_all(
        monkeypatch,
        {
            "check_db": ok_async,
            "check_redis": ok_async,
            "check_migrations": ok_sync,
            "check_storage": ok_async,
            "check_webhooks": ok_sync,
            "check_alertmanager": ok_async,
            "check_backups": ok_sync,
            "check_soft_delete_indexes": ok_sync,
            "check_quotas": ok_async,
            "check_webhook_metrics": ok_async,
            "check_replica": ok_async,
        },
    )
    client = TestClient(app)
    resp = client.get("/api/admin/preflight")
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "ok"
    assert len(body["checks"]) == 11


def test_preflight_fail(monkeypatch):
    _patch_all(
        monkeypatch,
        {
            "check_db": fail_async,
            "check_redis": ok_async,
            "check_migrations": ok_sync,
            "check_storage": ok_async,
            "check_webhooks": ok_sync,
            "check_alertmanager": ok_async,
            "check_backups": ok_sync,
            "check_soft_delete_indexes": ok_sync,
            "check_quotas": ok_async,
            "check_webhook_metrics": ok_async,
            "check_replica": ok_async,
        },
    )
    client = TestClient(app)
    resp = client.get("/api/admin/preflight")
    assert resp.json()["status"] == "fail"


def test_preflight_warn(monkeypatch):
    _patch_all(
        monkeypatch,
        {
            "check_db": ok_async,
            "check_redis": ok_async,
            "check_migrations": ok_sync,
            "check_storage": ok_async,
            "check_webhooks": warn_sync,
            "check_alertmanager": ok_async,
            "check_backups": ok_sync,
            "check_soft_delete_indexes": ok_sync,
            "check_quotas": ok_async,
            "check_webhook_metrics": ok_async,
            "check_replica": ok_async,
        },
    )
    client = TestClient(app)
    resp = client.get("/api/admin/preflight")
    assert resp.json()["status"] == "warn"

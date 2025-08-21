from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def test_backup_endpoint_creates_file(tmp_path, monkeypatch):
    db_path = tmp_path / "tenant_demo.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t (name) VALUES ('a')")
    conn.commit()
    conn.close()
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )

    import api.app.main as app_main
    importlib.reload(app_main)
    app = app_main.app

    class DummyRedis:
        async def sismember(self, *args, **kwargs):
            return False

        async def incr(self, *args, **kwargs):
            return 0

        async def sadd(self, *args, **kwargs):
            return 0

    app.state.redis = DummyRedis()

    client = TestClient(app)
    resp = client.post("/api/outlet/demo/backup")
    assert resp.status_code == 200
    out_file = Path(resp.json()["data"]["file"])
    try:
        assert out_file.exists()
        assert out_file.read_text().strip()
    finally:
        if out_file.exists():
            out_file.unlink()
        if out_file.parent.exists() and not any(out_file.parent.iterdir()):
            out_file.parent.rmdir()

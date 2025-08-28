# test_tenant_backup.py
import sqlite3
import subprocess
import sys
from pathlib import Path
import shutil
import pytest


def test_backup_creates_file(tmp_path, monkeypatch):
    db_path = tmp_path / "tenant_demo.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t (name) VALUES ('a')")
    conn.commit()
    conn.close()
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{'{tenant_id}'}.db",
    )
    out_file = tmp_path / "backup.json"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts" / "tenant_backup.py"),
            "--tenant",
            "demo",
            "--out",
            str(out_file),
        ],
        check=True,
    )
    assert out_file.exists()
    assert out_file.read_text().strip()


def test_pg_backup_invokes_pg_dump(tmp_path, monkeypatch):
    from scripts import tenant_backup

    monkeypatch.setattr(tenant_backup, "build_dsn", lambda tenant: "postgresql://foo")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/pg_dump")

    calls = {}

    def fake_run(cmd, check):
        calls["cmd"] = cmd
        Path(cmd[cmd.index("-f") + 1]).write_text("dump")

    monkeypatch.setattr(tenant_backup.subprocess, "run", fake_run)

    out_file = tmp_path / "backup.dump"
    tenant_backup.backup("demo", out_file)
    assert out_file.read_text() == "dump"
    assert calls["cmd"][0] == "/usr/bin/pg_dump"
    assert "-Fc" in calls["cmd"]


def test_pg_backup_missing_pg_dump(tmp_path, monkeypatch):
    from scripts import tenant_backup

    monkeypatch.setattr(tenant_backup, "build_dsn", lambda tenant: "postgresql://foo")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    with pytest.raises(FileNotFoundError, match="pg_dump"):
        tenant_backup.backup("demo", tmp_path / "backup.sql")


def test_pg_backup_sql_format(tmp_path, monkeypatch):
    from scripts import tenant_backup

    monkeypatch.setattr(tenant_backup, "build_dsn", lambda tenant: "postgresql://foo")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/pg_dump")

    calls = {}

    def fake_run(cmd, check):
        calls["cmd"] = cmd
        Path(cmd[cmd.index("-f") + 1]).write_text("dump")

    monkeypatch.setattr(tenant_backup.subprocess, "run", fake_run)

    out_file = tmp_path / "backup.sql"
    tenant_backup.backup("demo", out_file)
    assert "-Fc" not in calls["cmd"]

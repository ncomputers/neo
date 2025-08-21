# test_tenant_backup.py
import sqlite3
import subprocess
import sys
from pathlib import Path


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

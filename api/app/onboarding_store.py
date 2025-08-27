from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict

_DB_PATH = Path(
    os.getenv("ONBOARDING_DB", Path(tempfile.gettempdir()) / "onboarding.db")
)
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS onboarding_sessions (id TEXT PRIMARY KEY, data TEXT)"
        )
    return _conn


def load_session(onboarding_id: str) -> Dict[str, Any]:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT data FROM onboarding_sessions WHERE id=?", (onboarding_id,)
    )
    row = cur.fetchone()
    if row:
        return json.loads(row[0])
    session = {"id": onboarding_id, "current_step": "start"}
    conn.execute(
        "INSERT OR REPLACE INTO onboarding_sessions (id, data) VALUES (?, ?)",
        (onboarding_id, json.dumps(session)),
    )
    conn.commit()
    return session


def save_session(session: Dict[str, Any]) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO onboarding_sessions (id, data) VALUES (?, ?)",
        (session["id"], json.dumps(session)),
    )
    conn.commit()


def delete_session(onboarding_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM onboarding_sessions WHERE id=?", (onboarding_id,))
    conn.commit()


__all__ = ["load_session", "save_session", "delete_session"]

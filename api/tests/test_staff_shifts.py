import os
import sys
import pathlib
from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import os

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

from api.app.main import app, SessionLocal  # noqa: E402
from api.app.models_tenant import AuditTenant  # noqa: E402
from tests.conftest import DummyRedis  # noqa: E402

client = TestClient(app)


def setup_module():
    app.state.redis = DummyRedis()


def test_staff_shift_summary_csv():
    day = datetime.now(timezone.utc).date()
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    with SessionLocal() as session:
        session.add_all(
            [
                AuditTenant(actor="1:waiter", action="login", at=start + timedelta(hours=1)),
                AuditTenant(
                    actor="1:waiter", action="mark_table_ready", at=start + timedelta(hours=2)
                ),
                AuditTenant(
                    actor="1:waiter", action="mark_table_ready", at=start + timedelta(hours=3)
                ),
                AuditTenant(actor="2:cleaner", action="login", at=start + timedelta(hours=4)),
            ]
        )
        session.commit()
    date_str = day.isoformat()
    resp = client.get(f"/api/outlet/demo/staff/shifts?date={date_str}")
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert any(
        r["staff_id"] == 1 and r["logins"] == 1 and r["tables_cleaned"] == 2 for r in rows
    )
    assert any(r["staff_id"] == 2 and r["logins"] == 1 for r in rows)

    resp = client.get(f"/api/outlet/demo/staff/shifts?date={date_str}&format=csv")
    assert resp.status_code == 200
    lines = resp.text.splitlines()
    assert lines[0].startswith("staff_id,logins")
    assert any(line.startswith("1,1,0,2,0,") for line in lines[1:])

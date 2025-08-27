import os
import pathlib
import sys
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from fastapi import FastAPI
from fastapi.routing import APIRoute

from api.app import routes_retention  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_tenant import AuditTenant  # noqa: E402

app = FastAPI()
app.include_router(routes_retention.router)
for route in app.routes:
    if isinstance(route, APIRoute) and route.path.startswith("/api/admin/retention/"):
        for dep in route.dependant.dependencies:
            app.dependency_overrides[dep.call] = lambda: None

from contextlib import asynccontextmanager
from api.app.services import retention as retention_svc  # noqa: E402


@asynccontextmanager
async def _session_cm(_tenant: str):
    sync = SessionLocal()

    class _Wrapper:
        def __init__(self, s):
            self._s = s

        async def execute(self, *args, **kwargs):
            return self._s.execute(*args, **kwargs)

        async def commit(self):
            self._s.commit()

        def add(self, obj):
            self._s.add(obj)

    try:
        yield _Wrapper(sync)
    finally:
        sync.close()


retention_svc.get_tenant_session = _session_cm  # type: ignore


def setup_function() -> None:
    with SessionLocal() as session:
        session.execute(text("DELETE FROM customers"))
        session.execute(text("DELETE FROM invoices"))
        session.execute(text("DELETE FROM orders"))
        session.execute(text("DELETE FROM audit_tenant"))
        try:
            session.execute(text("ALTER TABLE customers ADD COLUMN created_at TIMESTAMP"))
            session.execute(text("ALTER TABLE customers ADD COLUMN email TEXT"))
        except Exception:
            pass
        try:
            session.execute(text("ALTER TABLE invoices ADD COLUMN name TEXT"))
            session.execute(text("ALTER TABLE invoices ADD COLUMN phone TEXT"))
            session.execute(text("ALTER TABLE invoices ADD COLUMN email TEXT"))
            session.execute(text("ALTER TABLE invoices ADD COLUMN created_at TIMESTAMP"))
        except Exception:
            pass
        session.commit()
        old = datetime.utcnow() - timedelta(days=40)
        recent = datetime.utcnow() - timedelta(days=5)
        session.execute(
            text(
                "INSERT INTO customers (id, name, phone, email, created_at, allow_analytics, allow_wa) "
                "VALUES (1, 'Old', '1', 'o@example.com', :dt, 0, 0)"
            ),
            {"dt": old},
        )
        session.execute(
            text(
                "INSERT INTO customers (id, name, phone, email, created_at, allow_analytics, allow_wa) "
                "VALUES (2, 'New', '2', 'n@example.com', :dt, 0, 0)"
            ),
            {"dt": recent},
        )
        session.execute(
            text(
                "INSERT INTO invoices (id, order_group_id, number, bill_json, total, settled, created_at, name, phone, email) "
                "VALUES (1,1,'a','{}',0,0,:dt,'Old','1','o@example.com')"
            ),
            {"dt": old},
        )
        session.execute(
            text(
                "INSERT INTO invoices (id, order_group_id, number, bill_json, total, settled, created_at, name, phone, email) "
                "VALUES (2,1,'b','{}',0,0,:dt,'New','2','n@example.com')"
            ),
            {"dt": recent},
        )
        session.execute(
            text(
                "INSERT INTO orders (id, table_id, status, placed_at) VALUES (1,1,'new', :dt)"
            ),
            {"dt": old},
        )
        session.execute(
            text(
                "INSERT INTO orders (id, table_id, status, placed_at) VALUES (2,1,'new', :dt)"
            ),
            {"dt": recent},
        )
        session.commit()


def test_preview_and_apply() -> None:
    client = TestClient(app)
    resp = client.post("/api/admin/retention/preview", json={"tenant": "t1", "days": 30})
    assert resp.status_code == 200
    assert resp.json()["data"] == {"customers": 1, "invoices": 1, "orders": 1}

    resp = client.post("/api/admin/retention/apply", json={"tenant": "t1", "days": 30})
    assert resp.status_code == 200
    assert resp.json()["data"] == {"customers": 1, "invoices": 1, "orders": 1}

    with SessionLocal() as session:
        cust = session.execute(
            text("SELECT name, phone, email FROM customers WHERE id = 1")
        ).one()
        assert cust == ("", "", "")
        inv = session.execute(
            text("SELECT name, phone, email FROM invoices WHERE id = 1")
        ).one()
        assert inv == ("", "", "")
        orders = session.execute(text("SELECT COUNT(*) FROM orders"))
        assert orders.scalar() == 1
        audit = session.query(AuditTenant).filter_by(action="retention.purge").count()
        assert audit == 1

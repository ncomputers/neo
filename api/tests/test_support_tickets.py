"""Tests for support ticket flows."""

from __future__ import annotations

import datetime
import pathlib
import sys
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.auth import create_access_token  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_master import SupportTicket  # noqa: E402
from api.app.routes_staff_support import router as staff_router  # noqa: E402
from api.app.routes_support import router as support_router  # noqa: E402

app = FastAPI()
app.include_router(support_router)
app.include_router(staff_router)


def owner_headers(tenant: str = "demo") -> dict:
    token = create_access_token({"sub": "owner@example.com", "role": "owner"})
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}


def staff_headers() -> dict:
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def _clear() -> None:
    with SessionLocal() as session:
        session.query(SupportTicket).delete()
        session.commit()


def test_ticket_creation_redaction() -> None:
    _clear()
    client = TestClient(app)
    resp = client.post(
        "/support/tickets",
        headers=owner_headers(),
        json={
            "subject": "Bug",
            "message": "Something broke",
            "channel": "email",
            "attachments": [],
            "includeDiagnostics": True,
            "diagnostics": {
                "log": "Bearer SECRET",
                "utr": "1234567890",
                "token": "token=abc",
            },
        },
    )
    assert resp.status_code == 200
    ticket_id = resp.json()["data"]["id"]
    with SessionLocal() as session:
        t = session.get(SupportTicket, uuid.UUID(ticket_id))
        assert t is not None
        assert t.diagnostics["log"] == "****"
        assert t.diagnostics["utr"] == "****"
        assert t.diagnostics["token"] == "****"


def test_listing_and_reply_updates() -> None:
    _clear()
    client = TestClient(app)
    resp = client.post(
        "/support/tickets",
        headers=owner_headers(),
        json={"subject": "Help", "message": "Issue"},
    )
    tid = resp.json()["data"]["id"]
    client.post(
        f"/support/tickets/{tid}/reply",
        headers=owner_headers(),
        json={"message": "Thanks"},
    )
    resp2 = client.get("/support/tickets", headers=owner_headers())
    ticket = [t for t in resp2.json()["data"] if t["id"] == tid][0]
    assert ticket["updated_at"] is not None


def test_rbac_owner_and_staff() -> None:
    _clear()
    client = TestClient(app)
    client.post(
        "/support/tickets",
        headers=owner_headers("demo"),
        json={"subject": "A", "message": "A"},
    )
    client.post(
        "/support/tickets",
        headers=owner_headers("other"),
        json={"subject": "B", "message": "B"},
    )
    resp_demo = client.get("/support/tickets", headers=owner_headers("demo"))
    assert len(resp_demo.json()["data"]) == 1
    resp_other = client.get("/support/tickets", headers=owner_headers("other"))
    assert len(resp_other.json()["data"]) == 1
    resp_forbidden = client.get("/staff/support", headers=owner_headers())
    assert resp_forbidden.status_code == 403
    resp_staff = client.get("/staff/support", headers=staff_headers())
    assert len(resp_staff.json()["data"]) == 2


def test_staff_filters() -> None:
    _clear()
    client = TestClient(app)
    client.post(
        "/support/tickets",
        headers=owner_headers("demo"),
        json={"subject": "A", "message": "A"},
    )
    client.post(
        "/support/tickets",
        headers=owner_headers("other"),
        json={"subject": "B", "message": "B"},
    )
    today = datetime.date.today().isoformat()
    resp_all = client.get("/staff/support", headers=staff_headers())
    assert len(resp_all.json()["data"]) == 2
    resp_tenant = client.get("/staff/support?tenant=demo", headers=staff_headers())
    assert len(resp_tenant.json()["data"]) == 1
    resp_date = client.get("/staff/support?date=2099-01-01", headers=staff_headers())
    assert len(resp_date.json()["data"]) == 0
    resp_today = client.get(f"/staff/support?date={today}", headers=staff_headers())
    assert len(resp_today.json()["data"]) == 2

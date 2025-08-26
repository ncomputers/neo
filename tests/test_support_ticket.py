from fastapi.testclient import TestClient

from api.app.auth import create_access_token
from api.app.main import app


def test_support_ticket_flow():
    client = TestClient(app)

    owner_token = create_access_token({"sub": "owner@example.com", "role": "owner"})
    owner_headers = {
        "Authorization": f"Bearer {owner_token}",
        "X-Tenant-ID": "t1",
    }

    resp = client.post(
        "/support/ticket",
        json={"subject": "Printer issue", "body": "It is jammed", "screenshots": []},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    ticket_id = resp.json()["data"]["id"]

    resp = client.get("/support/ticket", headers=owner_headers)
    assert resp.status_code == 200
    tickets = resp.json()["data"]
    assert any(t["id"] == ticket_id for t in tickets)

    admin_token = create_access_token(
        {"sub": "admin@example.com", "role": "super_admin"}
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/admin/support", headers=admin_headers)
    assert resp.status_code == 200
    tickets = resp.json()["data"]
    assert any(t["id"] == ticket_id and t["status"] == "open" for t in tickets)

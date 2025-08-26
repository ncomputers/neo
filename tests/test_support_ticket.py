from fastapi.testclient import TestClient

from api.app.main import app
from api.app.auth import create_access_token


def test_support_ticket_flow():
    client = TestClient(app)
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/support/ticket",
        json={"subject": "Printer issue", "body": "It is jammed", "screenshots": []},
        headers=headers,
    )
    assert resp.status_code == 200
    ticket_id = resp.json()["data"]["id"]

    resp = client.get("/admin/support", headers=headers)
    assert resp.status_code == 200
    tickets = resp.json()["data"]
    assert any(t["id"] == ticket_id and t["status"] == "open" for t in tickets)

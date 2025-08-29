import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from api.app.audit import Base, engine, log_event
from api.app.auth import create_access_token
from api.app.main import app

client = TestClient(app)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _auth() -> dict:
    token = create_access_token({"sub": "owner@example.com", "role": "owner"})
    return {"Authorization": f"Bearer {token}"}


def test_list_and_csv() -> None:
    log_event("staff", "order", "o1", master=True)
    resp = client.get("/admin/audit", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert any(r["action"] == "order" for r in body["data"])

    resp = client.get("/admin/audit?format=csv", headers=_auth())
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "actor,action" in resp.text

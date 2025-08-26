import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_admin_print import router


def test_admin_print_test_renders_template():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    payload = {
        "size": "80mm",
        "vars": {"header": "Sample", "items": [{"name": "Tea", "qty": 2}]},
    }
    resp = client.post("/admin/print/test", json=payload)
    assert resp.status_code == 200
    body = resp.text
    assert "Sample" in body
    assert "Tea x2" in body

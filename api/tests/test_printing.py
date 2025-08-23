import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_print import router


def test_print_test_route_returns_bytes():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/api/outlet/demo/print/test?size=80mm")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert len(resp.content) > 0
    assert resp.content.startswith(b"\x1b")

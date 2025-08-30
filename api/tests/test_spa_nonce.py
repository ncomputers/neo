import pathlib
import re
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from starlette.staticfiles import StaticFiles  # noqa: E402

from api.app.middleware.csp import CSPMiddleware  # noqa: E402


def test_spa_index_nonce(tmp_path):
    (tmp_path / "index.html").write_text('<script nonce="{{ csp_nonce }}"></script>')
    app = FastAPI()
    app.add_middleware(CSPMiddleware)
    app.mount("/", StaticFiles(directory=tmp_path, html=True))
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    m = re.search(r'nonce="([^"]+)"', resp.text)
    assert m
    nonce = m.group(1)
    assert f"nonce-{nonce}" in resp.headers["content-security-policy"]
    assert "{{ csp_nonce }}" not in resp.text

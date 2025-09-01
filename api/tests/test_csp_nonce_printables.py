import pathlib
import re
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import routes_kot  # noqa: E402
from api.app.middlewares.security import SecurityMiddleware  # noqa: E402
from api.app.middleware.csp import CSPMiddleware  # noqa: E402
from api.app.routes_invoice_pdf import router as invoice_router  # noqa: E402


def _extract_nonce(resp):
    csp = resp.headers["content-security-policy"]
    m = re.search(r"nonce-([^']+)'", csp)
    assert m is not None
    return m.group(1)


def test_invoice_csp_nonce():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CSPMiddleware)
    app.include_router(invoice_router)
    client = TestClient(app)
    resp = client.get("/invoice/123/pdf?size=80mm")
    assert resp.status_code == 200
    nonce = _extract_nonce(resp)
    assert f'<style nonce="{nonce}">' in resp.text


def test_kot_csp_nonce():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CSPMiddleware)
    app.include_router(routes_kot.router)

    class DummyResult1:
        def first(self):
            return (1, datetime(2023, 1, 1), "C1")

    class DummyResult2:
        def all(self):
            return [("Tea", 1, None)]

    class DummySession:
        def __init__(self):
            self.calls = 0

        async def execute(self, *args, **kwargs):
            self.calls += 1
            return DummyResult1() if self.calls == 1 else DummyResult2()

    async def fake_get_session_from_path(tenant_id: str):
        yield DummySession()

    app.dependency_overrides[
        routes_kot.get_session_from_path
    ] = fake_get_session_from_path

    client = TestClient(app)
    resp = client.get("/api/outlet/demo/kot/1.pdf")
    assert resp.status_code == 200
    nonce = _extract_nonce(resp)
    assert f'<style nonce="{nonce}">' in resp.text

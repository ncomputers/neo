import pathlib
import re
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.middlewares.security import SecurityMiddleware  # noqa: E402
from api.app.pdf import render as pdf_render  # noqa: E402
from api.app.routes_invoice_pdf import router  # noqa: E402


def test_invoice_pdf_route_html_fallback():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/invoice/123/pdf?size=80mm")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Invoice #INV-123" in resp.text
    csp = resp.headers["content-security-policy"]
    m = re.search(r"nonce-([^']+)'", csp)
    assert m is not None
    nonce = m.group(1)
    assert f'nonce="{nonce}"' in resp.text


def test_render_invoice_pdf_with_fake_weasyprint(monkeypatch):
    class DummyHTML:
        def __init__(self, string):
            self.string = string

        def write_pdf(self):
            return b"%PDF-1.4"

    class DummyWeasy:
        HTML = DummyHTML

    def fake_import(name):  # pragma: no cover - simple mock
        if name == "weasyprint":
            return DummyWeasy()
        raise ImportError

    monkeypatch.setattr(pdf_render.importlib, "import_module", fake_import)
    content, mimetype = pdf_render.render_invoice(
        {"number": "X", "items": [], "total": 0}, size="A4"
    )
    assert content.startswith(b"%PDF")
    assert mimetype == "application/pdf"


def test_kot_template_nonce(monkeypatch):
    def fake_import(name):
        raise ImportError

    monkeypatch.setattr(pdf_render.importlib, "import_module", fake_import)
    html_bytes, mimetype = pdf_render.render_template(
        "kot_80mm.html",
        {
            "kot": {
                "order_id": 1,
                "placed_at": "",
                "source_type": "Counter",
                "source_code": "1",
                "items": [],
            }
        },
        nonce="abc",
    )
    assert mimetype == "text/html"
    assert b'<style nonce="abc">' in html_bytes

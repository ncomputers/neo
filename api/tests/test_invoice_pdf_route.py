import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.app.routes_invoice_pdf import router
from api.app.pdf import render as pdf_render


def test_invoice_pdf_route_html_fallback():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/invoice/123/pdf?size=80mm")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Invoice #INV-123" in resp.text


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

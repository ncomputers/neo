import io
import pathlib
import re
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.middlewares.security import SecurityMiddleware  # noqa: E402
from api.app.pdf import render as pdf_render  # noqa: E402
from api.app.routes_invoice_pdf import router  # noqa: E402


def test_invoice_pdf_route_html_fallback(monkeypatch):
    def fake_import(name):
        raise ImportError

    monkeypatch.setattr(pdf_render.importlib, "import_module", fake_import)
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
    assert f'<style nonce="{nonce}">' in resp.text


def test_render_invoice_pdf_with_fake_weasyprint(monkeypatch):
    class DummyHTML:
        def __init__(self, string, base_url=None):
            self.string = string
            self.base_url = base_url

        def write_pdf(self, font_config=None):
            return b"%PDF-1.4"

    class DummyWeasy:
        HTML = DummyHTML

        class text:
            class fonts:
                class FontConfiguration:  # noqa: D401 - simple stub
                    """Font config stub."""

                    def __init__(self):
                        pass

                    def add_font_face(self, *args, **kwargs):
                        pass

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


def test_invoice_template_nonce(monkeypatch):
    def fake_import(name):
        raise ImportError

    monkeypatch.setattr(pdf_render.importlib, "import_module", fake_import)
    content, mimetype = pdf_render.render_invoice(
        {
            "number": "1",
            "items": [],
            "subtotal": 0,
            "grand_total": 0,
            "gst_mode": "unreg",
        },
        size="80mm",
        nonce="abc",
    )
    assert mimetype == "text/html"
    assert b'<style nonce="abc">' in content


def test_invoice_gujarati_item(monkeypatch):
    def fake_import(name):
        raise ImportError

    monkeypatch.setattr(pdf_render.importlib, "import_module", fake_import)
    html_bytes, mimetype = pdf_render.render_invoice(
        {
            "number": "1",
            "items": [{"name": "કાઠીયાવાડી", "qty": 1, "price": "₹1"}],
            "subtotal": "₹1",
            "grand_total": "₹1",
            "gst_mode": "unreg",
        }
    )
    text = html_bytes.decode("utf-8")
    assert "કાઠીયાવાડી" in text
    assert "₹" in text
    assert "Noto Sans" in text


def test_invoice_pdf_indic_fonts(tmp_path):
    invoice = {
        "number": "1",
        "items": [
            {"name": "કાઠીયાવાડી", "qty": 1, "price": "₹1"},
            {"name": "पाव भाजी", "qty": 1, "price": "₹2"},
        ],
        "subtotal": "₹3",
        "grand_total": "₹3",
        "gst_mode": "unreg",
    }
    pdf_bytes, mimetype = pdf_render.render_invoice(invoice)
    assert mimetype == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "કાઠીયાવાડી" in text
    assert "पाव भाजी" in text
    assert "₹" in text
    assert "\ufffd" not in text
    assert len(pdf_bytes) < 200_000

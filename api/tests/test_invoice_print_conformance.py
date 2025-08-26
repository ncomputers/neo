"""Invoice print conformance tests.

Ensures different GST modes render correct tax lines and that
optional FSSAI details appear when provided.
"""
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.pdf.render import render_invoice  # noqa: E402
from api.app.services import billing_service  # noqa: E402

ITEMS = [
    {"name": "Tea", "qty": 2, "price": 100, "gst": 5, "hsn": "1234"},
    {"name": "Coffee", "qty": 1, "price": 200, "gst": 12, "hsn": "5678"},
]
GSTIN = "22AAAAA0000A1Z5"
FSSAI_NO = "112233445566"


def _render(mode: str, **extras) -> str:
    """Render invoice for ``mode`` and return HTML string."""
    build_kwargs = {}
    if "is_interstate" in extras:
        build_kwargs["is_interstate"] = extras.pop("is_interstate")
    invoice = billing_service.build_invoice_context(ITEMS, mode, gstin=GSTIN, **build_kwargs)
    invoice["number"] = "INV-1"
    invoice.update(extras)
    html_bytes, mimetype = render_invoice(invoice, size="80mm")
    assert mimetype == "text/html"
    return html_bytes.decode("utf-8")


def test_regular_print():
    html = _render("reg")
    assert "GSTIN: 22AAAAA0000A1Z5" in html
    assert "GST%" in html
    assert "CGST" in html and "SGST" in html


def test_regular_print_interstate():
    html = _render("reg", is_interstate=True)
    assert "IGST" in html and "CGST" not in html and "SGST" not in html


def test_composition_print():
    html = _render("comp")
    assert "Composition Scheme" in html
    assert "GST%" not in html and "HSN" not in html
    assert "CGST" not in html and "SGST" not in html


def test_unregistered_print():
    html = _render("unreg")
    assert "GSTIN" not in html
    assert "GST%" not in html
    assert "CGST" not in html and "SGST" not in html and "IGST" not in html


def test_fssai_toggle():
    html = _render("reg", fssai=FSSAI_NO, show_fssai_logo=True)
    assert f"FSSAI: {FSSAI_NO}" in html
    assert "FSSAI Logo" in html

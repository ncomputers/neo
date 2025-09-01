import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.pdf.render import render_invoice
from api.app.services import billing_service

ITEMS = [
    {"name": "Tea", "qty": 2, "price": 100, "gst": 5, "hsn": "1234"},
    {"name": "Coffee", "qty": 1, "price": 200, "gst": 12, "hsn": "5678"},
]
GSTIN = "22AAAAA0000A1Z5"


def _render(mode: str, **kwargs) -> str:
    invoice = billing_service.build_invoice_context(ITEMS, mode, gstin=GSTIN, **kwargs)
    invoice["number"] = "INV-1"
    html_bytes, mimetype = render_invoice(invoice, size="80mm")
    assert mimetype == "text/html"
    return html_bytes.decode("utf-8")


def test_render_regular():
    html = _render("reg")
    assert "GSTIN: 22AAAAA0000A1Z5" in html
    assert "GST%" in html and "HSN" in html
    assert "CGST 2.5%" in html and "SGST 2.5%" in html
    assert "Composition Scheme" not in html
    assert "Tax not applicable" not in html


def test_render_regular_interstate():
    html = _render("reg", is_interstate=True)
    assert "GST%" in html and "HSN" in html
    assert "IGST 5%" in html and "CGST" not in html and "SGST" not in html


def test_render_composition():
    html = _render("comp")
    assert "GSTIN: 22AAAAA0000A1Z5 (Composition Scheme)" in html
    assert "GST%" not in html and "HSN" not in html
    assert "CGST" not in html and "SGST" not in html
    assert "Composition tax included" in html
    assert "Tax not applicable" not in html


def test_render_unregistered():
    html = _render("unreg")
    assert "GSTIN" not in html
    assert "GST%" not in html and "HSN" not in html
    assert "CGST" not in html and "SGST" not in html and "IGST" not in html
    assert "Tax not applicable" in html
    assert "Composition Scheme" not in html


def test_render_composition_scheme_flag():
    invoice = billing_service.build_invoice_context(ITEMS, "reg", gstin=GSTIN)
    invoice["number"] = "INV-1"
    invoice["composition_scheme"] = True
    html_bytes, mimetype = render_invoice(invoice, size="80mm")
    assert mimetype == "text/html"
    html = html_bytes.decode("utf-8")
    assert "GSTIN: 22AAAAA0000A1Z5 (Composition Scheme)" in html


def test_comp_invoice_no_gst_lines():
    invoice = billing_service.build_invoice_context(ITEMS, "comp", gstin=GSTIN)
    assert invoice["tax_lines"] == []


def test_item_level_gst_hsn():
    invoice = billing_service.build_invoice_context(ITEMS, "reg", gstin=GSTIN)
    assert invoice["items"][0]["gst"] == 5
    assert invoice["items"][0]["hsn"] == "1234"

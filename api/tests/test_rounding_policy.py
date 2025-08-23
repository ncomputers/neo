import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.pdf.render import render_invoice
from api.app.services import billing_service


def test_rounding_adjustment_calculation_and_rendering():
    items = [{"name": "Item", "qty": 1, "price": 99.99, "gst": 5}]
    bill = billing_service.compute_bill(items, "reg")
    assert bill["rounding_adjustment"] != 0
    subtotal = bill["subtotal"]
    tax_total = sum(bill["tax_breakup"].values())
    assert round(subtotal + tax_total + bill["rounding_adjustment"], 2) == bill["total"]

    invoice = billing_service.build_invoice_context(items, "reg")
    invoice["number"] = "INV-RND"
    html_bytes, _ = render_invoice(invoice, size="80mm")
    html = html_bytes.decode("utf-8")
    assert "Rounding Adj." in html

    items_int = [{"name": "Item", "qty": 1, "price": 100, "gst": 5}]
    invoice_int = billing_service.build_invoice_context(items_int, "reg")
    invoice_int["number"] = "INV-RND2"
    html_bytes_int, _ = render_invoice(invoice_int, size="80mm")
    assert "Rounding Adj." not in html_bytes_int.decode("utf-8")

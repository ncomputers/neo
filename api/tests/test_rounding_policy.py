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


def test_rounding_modes():
    items = [{"name": "Item", "qty": 1, "price": 2.5}]
    half_up = billing_service.compute_bill(items, "unreg", rounding_mode="half-up")
    bankers = billing_service.compute_bill(items, "unreg", rounding_mode="bankers")
    ceil = billing_service.compute_bill(items, "unreg", rounding_mode="ceil")
    floor = billing_service.compute_bill(items, "unreg", rounding_mode="floor")
    assert half_up["total"] == 3.0
    assert bankers["total"] == 2.0
    assert ceil["total"] == 3.0
    assert floor["total"] == 2.0


def test_gst_rounding_styles():
    items = [
        {"name": "A", "qty": 1, "price": 0.5, "gst": 5},
        {"name": "B", "qty": 1, "price": 0.5, "gst": 5},
    ]
    itemwise = billing_service.compute_bill(items, "reg", gst_rounding="item-wise")
    invoice_total = billing_service.compute_bill(
        items, "reg", gst_rounding="invoice-total"
    )
    assert itemwise["tax_breakup"][5] == 0.06
    assert invoice_total["tax_breakup"][5] == 0.05


def test_rounding_to_paise():
    items = [{"name": "X", "qty": 1, "price": 1.23, "gst": 5}]
    bill = billing_service.compute_bill(items, "reg", rounding="none")
    assert bill["rounding_adjustment"] == 0.0
    assert bill["total"] == 1.29

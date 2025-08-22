import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.services import billing_service


BASKET = [
    {"qty": 2, "price": 100, "gst": 5},
    {"qty": 1, "price": 200, "gst": 12},
]


def build_invoice_json(items, gst_mode, discount=0.0, tip=0.0):
    bill = billing_service.compute_bill(items, gst_mode, tip=tip)
    tax_lines = []
    if gst_mode == "reg":
        for rate, amount in bill["tax_breakup"].items():
            half_rate = rate / 2
            half_amount = round(amount / 2, 2)
            tax_lines.append({"label": f"CGST {half_rate}%", "amount": half_amount})
            tax_lines.append({"label": f"SGST {half_rate}%", "amount": half_amount})
    elif gst_mode == "comp":
        total_tax = round(bill["total"] - bill["subtotal"], 2)
        tax_lines.append({"label": "GST", "amount": total_tax})
    grand_total = round(bill["total"] - discount, 2)
    invoice = {"subtotal": bill["subtotal"], "tax_lines": tax_lines, "grand_total": grand_total}
    if discount:
        invoice["discount"] = discount
    if tip:
        invoice["tip"] = tip
    return bill, invoice


def test_unregistered_invoice():
    bill, invoice = build_invoice_json(BASKET, "unreg")
    assert bill == {"subtotal": 400.0, "tax_breakup": {}, "tip": 0.0, "total": 400.0}
    assert invoice == {"subtotal": 400.0, "tax_lines": [], "grand_total": 400.0}


def test_composition_invoice():
    bill, invoice = build_invoice_json(BASKET, "comp")
    assert bill == {"subtotal": 400.0, "tax_breakup": {}, "tip": 0.0, "total": 400.0}
    assert invoice == {
        "subtotal": 400.0,
        "tax_lines": [{"label": "GST", "amount": 0.0}],
        "grand_total": 400.0,
    }


def test_regular_gst_invoice():
    bill, invoice = build_invoice_json(BASKET, "reg")
    assert bill == {"subtotal": 400.0, "tax_breakup": {5: 10.0, 12: 24.0}, "tip": 0.0, "total": 434.0}
    assert invoice == {
        "subtotal": 400.0,
        "tax_lines": [
            {"label": "CGST 2.5%", "amount": 5.0},
            {"label": "SGST 2.5%", "amount": 5.0},
            {"label": "CGST 6.0%", "amount": 12.0},
            {"label": "SGST 6.0%", "amount": 12.0},
        ],
        "grand_total": 434.0,
    }


def test_discount_and_tip_invoice():
    bill, invoice = build_invoice_json(BASKET, "reg", discount=34.0, tip=10.0)
    assert bill == {"subtotal": 400.0, "tax_breakup": {5: 10.0, 12: 24.0}, "tip": 10.0, "total": 444.0}
    assert invoice == {
        "subtotal": 400.0,
        "tax_lines": [
            {"label": "CGST 2.5%", "amount": 5.0},
            {"label": "SGST 2.5%", "amount": 5.0},
            {"label": "CGST 6.0%", "amount": 12.0},
            {"label": "SGST 6.0%", "amount": 12.0},
        ],
        "discount": 34.0,
        "tip": 10.0,
        "grand_total": 410.0,
    }


def test_tip_does_not_change_tax_breakup():
    bill_base = billing_service.compute_bill(BASKET, "reg")
    bill_tip = billing_service.compute_bill(BASKET, "reg", tip=10.0)
    assert bill_base["tax_breakup"] == bill_tip["tax_breakup"]
    assert bill_tip["total"] == bill_base["total"] + 10.0

from api.app.services.billing_service import build_invoice_context


def test_mixed_rates():
    items = [
        {"name": "Burger", "qty": 1, "price": 100, "gst": 5, "hsn": "2106"},
        {"name": "Cola", "qty": 2, "price": 50, "gst": 12, "hsn": "2202"},
    ]
    invoice = build_invoice_context(items, "reg")
    assert invoice["grand_total"] == 217.0
    amounts = {line["label"]: line["amount"] for line in invoice["tax_lines"]}
    assert amounts == {
        "CGST 2.5%": 2.5,
        "SGST 2.5%": 2.5,
        "CGST 6.0%": 6.0,
        "SGST 6.0%": 6.0,
    }


def test_boundary_rounding():
    items = [{"name": "Mint", "qty": 1, "price": 0.1, "gst": 5}]
    invoice = build_invoice_context(items, "reg")
    assert invoice["grand_total"] == 0.12
    assert invoice["tax_lines"] == [
        {"label": "CGST 2.5%", "amount": 0.01},
        {"label": "SGST 2.5%", "amount": 0.01},
    ]


def test_composition_invoice():
    items = [{"name": "Tea", "qty": 1, "price": 100, "gst": 5}]
    invoice = build_invoice_context(items, "comp")
    assert invoice["tax_lines"] == []
    assert invoice["grand_total"] == 100.0

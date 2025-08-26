from api.app.services import billing_service


def test_modifiers_and_combos_pricing():
    items = [
        {
            "price": 100,
            "qty": 1,
            "gst": 5,
            "mods": [
                {"price": 20, "gst": 5},
                {"price": 10, "gst": 0},
            ],
            "combos": [
                {"price": 30, "gst": 5},
            ],
        }
    ]
    bill = billing_service.compute_bill(items, "reg", rounding="none")
    assert bill["subtotal"] == 160.0
    assert bill["tax_breakup"] == {5: 7.5}
    assert bill["total"] == 167.5

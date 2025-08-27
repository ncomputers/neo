from pathlib import Path


def test_checkout_refund_flow():
    html = Path("templates/checkout.html").read_text(encoding="utf-8")
    # legal links are covered elsewhere; here we check refund behaviour
    assert "Are you sure?" in html
    assert "confirm(" in html
    assert "Idempotency-Key" in html
    assert "/payments/" in html and "/refund" in html

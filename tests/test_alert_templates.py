def test_render_email_invoice_paid():
    from app.alerts.render import render_email

    subject, html = render_email(
        "invoice_paid.html",
        {
            "outlet_logo": "logo.png",
            "outlet_name": "My Outlet",
            "customer_name": "Alice",
            "invoice_number": "123",
            "amount": "10",
        },
        "Invoice paid for {{ customer_name }}",
    )
    assert subject and html
    assert "Alice" in subject
    assert "Alice" in html


def test_render_digest_wa():
    from app.alerts.render import render_message

    text = render_message(
        "digest_wa.txt",
        {
            "date": "2024-01-01",
            "orders": 5,
            "sales": 100,
            "avg_ticket": 20,
            "top_items": "Tea(2)",
        },
    )
    assert text
    assert "2024-01-01" in text
    assert "5" in text

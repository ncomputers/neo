from scripts.owner_insights import compute_deltas, generate_insights


def test_compute_deltas_arrows():
    current = {"orders": 10, "gross_sales": 200.0}
    previous = {"orders": 8, "gross_sales": 200.0}
    deltas = compute_deltas(current, previous)
    assert deltas["orders"].delta == 2
    assert deltas["orders"].arrow == "↑"
    assert deltas["gross_sales"].delta == 0
    assert deltas["gross_sales"].arrow == "→"


def test_generate_insights_rules():
    metrics = {
        "sla_hit_rate": 0.8,
        "cancellations_by_item": {"Burger": 40, "Pizza": 10},
        "coupon_order_pct": 0.2,
        "aov_delta": -1,
        "referral_clicks": 5,
        "referral_conversions": 0,
    }
    insights = generate_insights(metrics)
    assert any("SLA hit rate" in msg for msg in insights)
    assert any("Burger" in msg for msg in insights)
    assert any("coupon" in msg.lower() for msg in insights)
    assert any("referral" in msg.lower() for msg in insights)

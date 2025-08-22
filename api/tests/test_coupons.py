import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest

from api.app.services import billing_service


def test_non_stackable_coupons_rejected():
    items = [{"price": 100}]
    c1 = {"code": "A", "percent": 10, "is_stackable": False}
    c2 = {"code": "B", "flat": 5, "is_stackable": False}
    with pytest.raises(ValueError) as exc:
        billing_service.compute_bill(items, "unreg", coupons=[c1, c2])
    assert "cannot be stacked" in str(exc.value)


def test_stackable_coupons_with_cap():
    items = [{"price": 200}]
    c1 = {"code": "C1", "percent": 5, "is_stackable": True, "max_discount": 15}
    c2 = {"code": "C2", "percent": 5, "is_stackable": True}
    bill = billing_service.compute_bill(items, "unreg", coupons=[c1, c2])
    assert bill["applied_coupons"] == ["C1", "C2"]
    assert bill["effective_discount"] == 15.0
    assert bill["total"] == 185.0

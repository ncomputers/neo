import pathlib
import sys
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.services import billing_service  # noqa: E402

# strategies for random bills and coupons
item_strategy = st.lists(
    st.fixed_dictionaries(
        {
            "price": st.integers(min_value=1, max_value=1000),
            "qty": st.integers(min_value=1, max_value=5),
        }
    ),
    min_size=1,
    max_size=5,
)

coupon_strategy = st.builds(
    lambda code, percent, flat, max_disc: {
        k: v
        for k, v in {
            "code": code,
            "is_stackable": True,
            "percent": percent if percent else None,
            "flat": flat if flat else None,
            "max_discount": max_disc,
        }.items()
        if v is not None
    },
    code=st.text(min_size=1, max_size=5),
    percent=st.integers(min_value=0, max_value=50),
    flat=st.integers(min_value=0, max_value=200),
    max_disc=st.one_of(st.none(), st.integers(min_value=1, max_value=500)),
).filter(lambda c: "percent" in c or "flat" in c)

coupons_strategy = st.lists(coupon_strategy, min_size=1, max_size=5).filter(
    lambda cs: any("max_discount" in c for c in cs)
)


@given(items=item_strategy, coupons=coupons_strategy)
def test_stackable_coupons_respect_caps(items, coupons):
    """Stacked coupons should never exceed the smallest max_discount."""
    bill = billing_service.compute_bill(items, "unreg", coupons=coupons)
    caps = [Decimal(str(c["max_discount"])) for c in coupons if "max_discount" in c]
    discount = Decimal(str(bill["effective_discount"]))
    assert discount <= min(caps)

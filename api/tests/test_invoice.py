import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import date

from api.app.invoice import (
    GSTType,
    Invoice,
    InvoiceItem,
    InvoiceNumberGenerator,
    Payment,
    consolidate_invoices,
)


def test_invoice_totals_and_payments():
    items = [
        InvoiceItem(name="Tea", quantity=2, price=10.0, gst_rate=0.05),
        InvoiceItem(name="Cake", quantity=1, price=50.0, gst_rate=0.18),
    ]
    invoice = Invoice(session_id="s1", gst_type=GSTType.REGULAR, items=items)
    invoice.tips = 5.0
    invoice.discount = 10.0
    invoice.service_charge = 2.0
    invoice.coupon_value = 5.0
    invoice.add_payment(Payment(method="upi", amount=30.0, verified=True))
    invoice.add_payment(Payment(method="cash", amount=40.0))

    assert round(invoice.subtotal(), 2) == 70.0
    assert round(invoice.gst_total(), 2) == 10.0
    assert round(invoice.total(), 2) == 72.0
    assert invoice.amount_paid() == 70.0
    assert not invoice.is_paid()


def test_invoice_number_reset_policy():
    gen = InvoiceNumberGenerator(prefix="INV", reset="daily")
    n1 = gen.next_number(date(2023, 1, 1))
    n2 = gen.next_number(date(2023, 1, 1))
    n3 = gen.next_number(date(2023, 1, 2))
    assert n1 == "INV0001"
    assert n2 == "INV0002"
    assert n3 == "INV0001"


def test_consolidate_invoices():
    gen = InvoiceNumberGenerator(prefix="C")
    inv1 = Invoice(session_id="s1", gst_type=GSTType.REGULAR)
    inv1.items.append(InvoiceItem(name="Item1", quantity=1, price=10.0, gst_rate=0.1))
    inv2 = Invoice(session_id="s1", gst_type=GSTType.REGULAR)
    inv2.items.append(InvoiceItem(name="Item2", quantity=2, price=20.0, gst_rate=0.1))
    merged = consolidate_invoices("s1", [inv1, inv2], gen)
    assert merged.number == "C0001"
    assert len(merged.items) == 2

"""Invoice data structures and rendering helpers."""

# invoice.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Iterable


class GSTType(str, Enum):
    """Supported GST registration modes."""

    UNREGISTERED = "unregistered"
    COMPOSITION = "composition"
    REGULAR = "regular"


@dataclass
class InvoiceItem:
    """Single line item on an invoice."""

    name: str
    quantity: int
    price: float
    gst_rate: float = 0.0

    def total(self) -> float:
        return self.quantity * self.price


@dataclass
class Payment:
    """Record of a payment against an invoice."""

    method: str  # e.g. "upi" or "cash"
    amount: float
    verified: bool = False


@dataclass
class Invoice:
    """Invoice with support for discounts, tips and split payments."""

    session_id: str
    gst_type: GSTType
    items: list[InvoiceItem] = field(default_factory=list)
    tips: float = 0.0
    discount: float = 0.0
    service_charge: float = 0.0
    coupon_value: float = 0.0
    payments: list[Payment] = field(default_factory=list)
    number: str | None = None

    def subtotal(self) -> float:
        return sum(item.total() for item in self.items)

    def gst_total(self) -> float:
        if self.gst_type is GSTType.UNREGISTERED:
            return 0.0
        return sum(item.total() * item.gst_rate for item in self.items)

    def total(self) -> float:
        return (
            self.subtotal()
            + self.gst_total()
            + self.tips
            + self.service_charge
            - self.discount
            - self.coupon_value
        )

    def add_payment(self, payment: Payment) -> None:
        self.payments.append(payment)

    def amount_paid(self) -> float:
        return sum(p.amount for p in self.payments)

    def is_paid(self) -> bool:
        return self.amount_paid() >= self.total()


class InvoiceNumberGenerator:
    """Generates invoice numbers with a reset policy."""

    def __init__(self, prefix: str = "", reset: str = "never") -> None:
        self.prefix = prefix
        self.reset = reset  # "daily", "monthly", "yearly", "never"
        self._counters: dict[str, int] = {}

    def _period_key(self, today: date) -> str:
        if self.reset == "daily":
            return today.isoformat()
        if self.reset == "monthly":
            return today.strftime("%Y-%m")
        if self.reset == "yearly":
            return str(today.year)
        return "global"

    def next_number(self, today: date | None = None) -> str:
        today = today or date.today()
        key = self._period_key(today)
        self._counters[key] = self._counters.get(key, 0) + 1
        return f"{self.prefix}{self._counters[key]:04d}"


def consolidate_invoices(
    session_id: str,
    invoices: Iterable[Invoice],
    number_generator: InvoiceNumberGenerator,
) -> Invoice:
    """Merge multiple invoices for a session into a single invoice."""

    merged = Invoice(session_id=session_id, gst_type=GSTType.REGULAR)
    for inv in invoices:
        merged.items.extend(inv.items)
        merged.tips += inv.tips
        merged.discount += inv.discount
        merged.service_charge += inv.service_charge
        merged.coupon_value += inv.coupon_value
        merged.payments.extend(inv.payments)
    merged.number = number_generator.next_number()
    return merged


def render_thermal(invoice: Invoice) -> str:
    """Render a simple 80mm thermal invoice."""

    lines = [f"Invoice {invoice.number}"]
    for item in invoice.items:
        lines.append(f"{item.name} x{item.quantity} {item.total():.2f}")
    lines.append(f"Total: {invoice.total():.2f}")
    return "\n".join(lines)


def render_pdf(invoice: Invoice) -> str:
    """Stub for A4/PDF invoice generation."""

    return f"PDF invoice {invoice.number} with total {invoice.total():.2f}"

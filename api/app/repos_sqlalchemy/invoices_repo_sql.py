"""SQLAlchemy implementation for invoice persistence."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from ..db.master import get_session as get_master_session
from ..models_master import Tenant
from ..models_tenant import Invoice, MenuItem, Order, OrderItem, Payment, Table
from ..hooks.table_map import publish_table_state
from ..services import billing_service
from ..utils import invoice_counter


async def generate_invoice(
    session: AsyncSession,
    order_group_id: int,
    gst_mode: billing_service.GSTMode,
    rounding: str,
    tenant_id: str,
    tip: float | Decimal | None = 0,
) -> int:
    """Generate an immutable invoice and return its primary key.

    Parameters
    ----------
    session:
        Active :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
    order_group_id:
        Identifier representing the group of orders to invoice.
    gst_mode:
        GST registration mode.
    rounding:
        Rounding strategy passed to :func:`billing_service.compute_bill`.
    tenant_id:
        Identifier of the tenant to fetch prefix and reset policy from the
        master schema.
    tip:
        Optional tip amount added after tax.
    """

    result = await session.execute(
        select(OrderItem.qty, OrderItem.price_snapshot, MenuItem.gst_rate)
        .join(Order, Order.id == OrderItem.order_id)
        .join(MenuItem, MenuItem.id == OrderItem.item_id)
        .where(Order.id == order_group_id)
    )

    items = [
        {"qty": qty, "price": float(price), "gst": float(gst or 0)}
        for qty, price, gst in result.all()
    ]

    bill = billing_service.compute_bill(items, gst_mode, rounding, tip=tip)

    async with get_master_session() as m_session:
        tenant = await m_session.get(Tenant, tenant_id)

    prefix = tenant.invoice_prefix or "INV"
    reset = tenant.invoice_reset or "never"
    series = invoice_counter.build_series(prefix, reset, date.today())
    number = await invoice_counter.next_invoice_number(session, series)

    invoice = Invoice(
        order_group_id=order_group_id,
        number=number,
        bill_json=bill,
        gst_breakup=bill.get("tax_breakup"),
        tip=Decimal(str(bill.get("tip", 0))),
        total=Decimal(str(bill["total"])),
    )
    session.add(invoice)
    await session.flush()
    return invoice.id


async def add_payment(
    session: AsyncSession,
    invoice_id: int,
    mode: str,
    amount: float,
    utr: str | None = None,
    verified: bool = False,
) -> None:
    """Record a payment against ``invoice_id``."""

    payment = Payment(
        invoice_id=invoice_id,
        mode=mode,
        amount=Decimal(str(amount)),
        utr=utr,
        verified=verified,
    )
    session.add(payment)
    await session.flush()

    total_paid = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id == invoice_id, Payment.verified
        )
    )
    invoice = await session.get(Invoice, invoice_id)
    if total_paid >= invoice.total:
        invoice.settled = True
        invoice.settled_at = datetime.now(timezone.utc)
        order = await session.get(Order, invoice.order_group_id)
        if order is not None:
            table = await session.get(Table, order.table_id)
            if table is not None:
                table.state = "LOCKED"
                await session.flush()
                await publish_table_state(table)
                return
    await session.flush()


async def list_day(
    session: AsyncSession, day: date, tz: str = "UTC"
) -> list[dict]:
    """Return invoices and payments for ``day`` in ``tz`` timezone."""

    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    result = await session.execute(
        select(
            Invoice.id,
            Invoice.number,
            Invoice.bill_json,
            Invoice.total,
            Payment.mode,
            Payment.amount,
        )
        .outerjoin(Payment, Payment.invoice_id == Invoice.id)
        .where(Invoice.created_at >= start, Invoice.created_at <= end)
    )

    rows = result.all()
    invoices: dict[int, dict] = {}
    for inv_id, number, bill, total, mode, amount in rows:
        entry = invoices.setdefault(
            inv_id,
            {
                "number": number,
                "subtotal": bill.get("subtotal", 0),
                "tax": sum(bill.get("tax_breakup", {}).values()),
                "total": float(total),
                "payments": [],
            },
        )
        if mode is not None:
            entry["payments"].append({"mode": mode, "amount": float(amount)})

    for entry in invoices.values():
        paid = sum(p["amount"] for p in entry["payments"])
        entry["settled"] = paid >= entry["total"]

    return list(invoices.values())

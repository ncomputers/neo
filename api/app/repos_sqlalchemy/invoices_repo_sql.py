from __future__ import annotations

"""SQLAlchemy implementation for invoice persistence."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.master import get_session as get_master_session
from ..models_master import Tenant
from ..models_tenant import Invoice, MenuItem, Order, OrderItem, Payment
from ..services import billing_service
from ..utils import invoice_counter


async def generate_invoice(
    session: AsyncSession,
    order_group_id: int,
    gst_mode: billing_service.GSTMode,
    rounding: str,
    tenant_id: str,
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

    bill = billing_service.compute_bill(items, gst_mode, rounding)

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

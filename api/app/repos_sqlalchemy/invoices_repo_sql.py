"""SQLAlchemy implementation for invoice persistence."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo
from typing import Mapping, Sequence

from ..db.master import get_session as get_master_session
from ..models_master import Tenant
from ..models_tenant import (
    Coupon,
    CouponUsage,
    Invoice,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    Table,
)
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
    coupons: Sequence[Mapping[str, object]] | None = None,
    *,
    guest_id: int | None = None,
    outlet_id: int | None = None,
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

    if coupons:
        await _enforce_coupon_caps(
            session, coupons, guest_id=guest_id, outlet_id=outlet_id
        )

    bill = billing_service.compute_bill(
        items, gst_mode, rounding, tip=tip, coupons=coupons
    )

    async with get_master_session() as m_session:
        tenant = await m_session.get(Tenant, tenant_id)

    prefix = tenant.inv_prefix or "GEN"
    reset = tenant.inv_reset or "never"
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


async def _enforce_coupon_caps(
    session: AsyncSession,
    coupons: Sequence[Mapping[str, object]],
    *,
    guest_id: int | None,
    outlet_id: int | None,
) -> None:
    """Validate coupon caps and record usage."""

    now = datetime.now(timezone.utc)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    for c in coupons:
        coupon = await session.scalar(select(Coupon).where(Coupon.code == c["code"]))
        if coupon is None:
            continue
        if coupon.valid_from and now < coupon.valid_from:
            raise billing_service.CouponError(
                "NOT_ACTIVE", f"Coupon {coupon.code} starts {coupon.valid_from.date()}"
            )
        if coupon.valid_to and now > coupon.valid_to:
            raise billing_service.CouponError(
                "EXPIRED", f"Coupon {coupon.code} expired on {coupon.valid_to.date()}"
            )

        if coupon.per_day_cap is not None:
            day_count = await session.scalar(
                select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.used_at >= start,
                    CouponUsage.used_at <= end,
                )
            )
            if day_count >= coupon.per_day_cap:
                raise billing_service.CouponError(
                    "DAILY_CAP", f"Coupon {coupon.code} limit reached today"
                )

        if guest_id is not None and coupon.per_guest_cap is not None:
            guest_count = await session.scalar(
                select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.guest_id == guest_id,
                )
            )
            if guest_count >= coupon.per_guest_cap:
                raise billing_service.CouponError(
                    "GUEST_CAP", f"Coupon {coupon.code} already used"
                )

        if outlet_id is not None and coupon.per_outlet_cap is not None:
            outlet_count = await session.scalar(
                select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.outlet_id == outlet_id,
                )
            )
            if outlet_count >= coupon.per_outlet_cap:
                raise billing_service.CouponError(
                    "OUTLET_CAP", f"Outlet limit reached for {coupon.code}"
                )

        session.add(
            CouponUsage(
                coupon_id=coupon.id, guest_id=guest_id, outlet_id=outlet_id
            )
        )


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
    session: AsyncSession, day: date, tz: str = "UTC", tenant_id: str | None = None
) -> list[dict]:
    """Return invoices and payments for ``day`` in ``tz`` timezone.

    The ``tenant_id`` argument is used purely for guard assertions to ensure the
    session is bound to the correct tenant database.
    """

    from . import TenantGuard

    TenantGuard.assert_tenant(session, tenant_id or "")

    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    result = await session.execute(
        select(
            Invoice.id,
            Invoice.number,
            Invoice.bill_json,
            Invoice.tip,
            Invoice.total,
            Payment.mode,
            Payment.amount,
        )
        .outerjoin(Payment, Payment.invoice_id == Invoice.id)
        .where(Invoice.created_at >= start, Invoice.created_at <= end)
    )

    rows = result.all()
    invoices: dict[int, dict] = {}
    for inv_id, number, bill, tip, total, mode, amount in rows:
        entry = invoices.setdefault(
            inv_id,
            {
                "number": number,
                "subtotal": bill.get("subtotal", 0),
                "tax": sum(bill.get("tax_breakup", {}).values()),
                "tip": float(tip or 0),
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

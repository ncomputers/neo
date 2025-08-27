from __future__ import annotations

"""Helpers for previewing and applying tenant data retention."""

from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import text

from ..db.tenant import get_tenant_session
from ..models_tenant import AuditTenant


async def preview(tenant: str, days: int) -> Dict[str, int]:
    """Return counts of records affected by retention."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with get_tenant_session(tenant) as session:
        cust = await session.execute(
            text("SELECT COUNT(*) FROM customers WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        inv = await session.execute(
            text("SELECT COUNT(*) FROM invoices WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        orders = await session.execute(
            text("SELECT COUNT(*) FROM orders WHERE placed_at < :cutoff"),
            {"cutoff": cutoff},
        )
    return {
        "customers": int(cust.scalar() or 0),
        "invoices": int(inv.scalar() or 0),
        "orders": int(orders.scalar() or 0),
    }


async def apply(tenant: str, days: int) -> Dict[str, int]:
    """Anonymize PII and purge old orders for ``tenant``."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with get_tenant_session(tenant) as session:
        cust_res = await session.execute(
            text(
                "UPDATE customers SET name = '', phone = '', email = '' "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        inv_res = await session.execute(
            text(
                "UPDATE invoices SET name = '', phone = '', email = '' "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        await session.execute(
            text(
                "DELETE FROM order_items WHERE order_id IN ("
                "SELECT id FROM orders WHERE placed_at < :cutoff)"
            ),
            {"cutoff": cutoff},
        )
        ord_res = await session.execute(
            text("DELETE FROM orders WHERE placed_at < :cutoff"),
            {"cutoff": cutoff},
        )
        session.add(
            AuditTenant(
                actor="system",
                action="retention.purge",
                meta={
                    "cutoff": cutoff.isoformat(),
                    "customers": cust_res.rowcount or 0,
                    "invoices": inv_res.rowcount or 0,
                    "orders": ord_res.rowcount or 0,
                },
            )
        )
        await session.commit()
    return {
        "customers": cust_res.rowcount or 0,
        "invoices": inv_res.rowcount or 0,
        "orders": ord_res.rowcount or 0,
    }


__all__ = ["preview", "apply"]

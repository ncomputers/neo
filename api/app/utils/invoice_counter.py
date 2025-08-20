from __future__ import annotations

"""Helpers to generate sequential invoice numbers."""

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_tenant import Invoice


async def next_invoice_number(session: AsyncSession) -> str:
    """Return the next invoice number as a string.

    The number is derived by taking the maximum existing invoice number and
    incrementing it by one. This assumes invoice numbers are numeric strings.
    """

    result = await session.execute(select(func.max(cast(Invoice.number, Integer))))
    current = result.scalar() or 0
    return str(current + 1)

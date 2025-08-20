"""Utilities for managing invoice counters."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_invoice_number(session: AsyncSession, series: str = "INV") -> str:
    """Return the next invoice number for ``series``.

    The counter is created if missing and atomically incremented.
    The resulting invoice number is formatted as ``SERIES/000001``.
    """
    stmt = text(
        """
        INSERT INTO invoice_counters (series, current)
        VALUES (:series, 1)
        ON CONFLICT (series)
        DO UPDATE SET current = invoice_counters.current + 1
        RETURNING current
        """
    )
    result = await session.execute(stmt, {"series": series})
    current = result.scalar_one()
    await session.commit()
    return f"{series}/{current:06d}"

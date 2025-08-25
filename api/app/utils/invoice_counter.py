"""Utilities for managing invoice counters."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def build_series(prefix: str, reset: str, today: date | None = None) -> str:
    """Return the series string for ``prefix`` and ``reset`` policy.

    The resulting value acts as the persistence key in
    :mod:`invoice_counters`. It excludes the constant ``INV`` prefix and the
    zero-padded counter suffix which are appended by
    :func:`next_invoice_number`.
    """
    today = today or date.today()
    if reset == "monthly":
        return f"{prefix}-{today:%Y%m}"
    if reset == "yearly":
        return f"{prefix}-{today:%Y}"
    return prefix


async def next_invoice_number(session: AsyncSession, series: str) -> str:
    """Return the next invoice number for ``series``.

    ``series`` should already include any prefix and reset components, e.g.
    ``PFX-202405`` for a monthly reset. The counter is created if missing and
    atomically incremented. The resulting invoice number is formatted as
    ``INV-SERIES-0001`` with a four-digit, zero-padded counter.
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
    return f"INV-{series}-{current:04d}"

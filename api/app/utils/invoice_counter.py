"""Utilities for managing invoice counters."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def build_series(prefix: str, reset: str, today: date | None = None) -> str:
    """Return a counter series incorporating ``prefix`` and ``reset`` policy.

    Parameters
    ----------
    prefix:
        String prefix for the invoice number.
    reset:
        Policy determining when counters reset – ``monthly``, ``yearly`` or
        ``never``.
    today:
        Date used for generating the series. Defaults to ``date.today()``.
    """
    today = today or date.today()
    if reset == "monthly":
        return f"{prefix}/{today:%Y}/{today:%m}"
    if reset == "yearly":
        return f"{prefix}/{today:%Y}"
    return prefix


async def next_invoice_number(session: AsyncSession, series: str) -> str:
    """Return the next invoice number for ``series``.

    ``series`` should already include any prefix and reset components, e.g.
    ``PFX/2024/05`` for a monthly reset. The counter is created if missing and
    atomically incremented. The resulting invoice number is formatted as
    ``SERIES/000001``.
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

"""Exponential moving average helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..repos_sqlalchemy import ema_repo_sql


def update_ema(prev: float | None, sample_seconds: float, n: int) -> float:
    """Return the updated EMA given a new sample.

    Parameters
    ----------
    prev:
        Previous EMA value. If ``None``, ``sample_seconds`` is returned.
    sample_seconds:
        The latest sample value in seconds.
    n:
        Window size used for the EMA calculation.
    """
    alpha = 2 / (n + 1)
    return (
        sample_seconds if prev is None else alpha * sample_seconds + (1 - alpha) * prev
    )


def eta(current_items: list[float], ema: float) -> float:
    """Estimate the ETA for a new item using a simple heuristic.

    The function assumes items are processed sequentially. ``current_items``
    contains the remaining prep times in seconds for items already queued. The
    EMA is treated as the expected prep time for the new item.
    """
    return sum(current_items) + ema


async def record_sample(
    session: AsyncSession, sample_seconds: float, n: int = 10
) -> float:
    """Update and persist the EMA given a new ``sample_seconds``.

    Parameters
    ----------
    session:
        Tenant-bound database session.
    sample_seconds:
        The latest sample value in seconds.
    n:
        Window size for EMA if no previous value exists. Defaults to 10.
    """
    current = await ema_repo_sql.load(session)
    prev = current[1] if current else None
    window = current[0] if current else n
    ema = update_ema(prev, sample_seconds, window)
    await ema_repo_sql.save(session, window, ema)
    return ema

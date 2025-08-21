"""Repository helpers for EMA persistence in tenant DB."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_tenant import EMAStat


async def load(session: AsyncSession) -> tuple[int, float] | None:
    """Return the current EMA window and value if present."""
    result = await session.execute(
        select(EMAStat.window_n, EMAStat.ema_seconds).limit(1)
    )
    row = result.first()
    if row:
        return row.window_n, float(row.ema_seconds)
    return None


async def save(session: AsyncSession, window_n: int, ema_seconds: float) -> None:
    """Persist ``ema_seconds`` for ``window_n`` in ``ema_stats`` table."""
    existing = await session.scalar(select(EMAStat.id))
    if existing is None:
        session.add(EMAStat(window_n=window_n, ema_seconds=ema_seconds))
    else:
        await session.execute(
            update(EMAStat)
            .where(EMAStat.id == existing)
            .values(window_n=window_n, ema_seconds=ema_seconds)
        )
    await session.commit()

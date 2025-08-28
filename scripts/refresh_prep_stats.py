from __future__ import annotations

"""Nightly job to refresh per-item prep time statistics."""

import asyncio
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.app.models_master import PrepStats

MIN_SAMPLES = 5


def summarize(samples: Iterable[float]) -> dict | None:
    """Return quantile summary for ``samples`` or ``None`` if too small."""
    data = list(samples)
    if len(data) < MIN_SAMPLES:
        return None
    p50 = statistics.median(data)
    qs = statistics.quantiles(data, n=100)
    return {
        "p50_s": int(p50),
        "p80_s": int(qs[79]),
        "p95_s": int(qs[94]),
        "sample_n": len(data),
    }


async def refresh(session: AsyncSession) -> None:
    """Placeholder implementation scanning recent items and upserting stats."""
    # In a real implementation this would query completed order items from the
    # last 30 days and aggregate durations by ``item_id`` and ``outlet_id``.
    # Here we simply demonstrate the upsert logic on existing ``prep_stats``.
    yesterday = datetime.utcnow() - timedelta(days=1)
    result = await session.execute(select(PrepStats))
    rows = result.scalars().all()
    for row in rows:
        stats = summarize([row.p50_s])
        if not stats:
            continue
        row.p50_s = stats["p50_s"]
        row.p80_s = stats["p80_s"]
        row.p95_s = stats["p95_s"]
        row.sample_n = stats["sample_n"]
        row.updated_at = datetime.utcnow()
    await session.commit()


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///./dev_master.db")
    async with AsyncSession(engine) as session:
        await refresh(session)


if __name__ == "__main__":
    asyncio.run(main())

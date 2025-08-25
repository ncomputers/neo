import pathlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import fakeredis.aioredis
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from api.app.models_master import Base as MasterBase, Tenant  # type: ignore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_once_per_day(tmp_path, monkeypatch):
    master_url = f"sqlite+aiosqlite:///{tmp_path}/master.db"
    engine = create_async_engine(master_url)
    async with engine.begin() as conn:
        await conn.run_sync(MasterBase.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        session.add(Tenant(name="t1", timezone="Asia/Kolkata", status="active"))
        await session.commit()

    fake_redis = fakeredis.aioredis.FakeRedis()
    calls: list[tuple[str, str]] = []

    async def fake_main(tenant: str, date_str: str, providers=None):
        calls.append((tenant, date_str))

    import scripts.digest_scheduler as ds
    monkeypatch.setattr(ds.daily_digest, "main", fake_main)
    monkeypatch.setattr(ds.daily_digest, "PROVIDERS", {"console": object()})

    tz = ZoneInfo("Asia/Kolkata")
    times = iter(
        [
            datetime(2024, 1, 1, 8, 55, tzinfo=tz),
            datetime(2024, 1, 1, 9, 1, tzinfo=tz),
            datetime(2024, 1, 1, 9, 5, tzinfo=tz),
            datetime(2024, 1, 2, 8, 59, tzinfo=tz),
            datetime(2024, 1, 2, 9, 1, tzinfo=tz),
        ]
    )
    monkeypatch.setattr(ds, "_now", lambda tzinfo: next(times))

    for _ in range(5):
        await ds.run_once(engine, fake_redis)

    assert calls == [("t1", "2023-12-31"), ("t1", "2024-01-01")]

    await fake_redis.close()
    await engine.dispose()

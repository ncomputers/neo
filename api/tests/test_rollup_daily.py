import pathlib
import sys
from datetime import datetime, date

import fakeredis.aioredis
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from scripts import rollup_daily  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_rollup_daily_lock_and_metrics(monkeypatch):
    fake_redis = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr(rollup_daily, "redis", fakeredis.aioredis)
    monkeypatch.setattr(rollup_daily.redis, "from_url", lambda url: fake_redis, raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://test")

    class DummyEngine:
        async def dispose(self):
            pass

    monkeypatch.setattr(rollup_daily, "get_tenant_engine", lambda tenant: DummyEngine())

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    def fake_sessionmaker(*args, **kwargs):
        return lambda: DummySession()

    monkeypatch.setattr(rollup_daily, "async_sessionmaker", fake_sessionmaker)

    calls: list[date] = []

    async def fake_rollup_day(session, tenant, day, tz):
        calls.append(day)

    monkeypatch.setattr(rollup_daily, "rollup_day", fake_rollup_day)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 3, tzinfo=tz)

    monkeypatch.setattr(rollup_daily, "datetime", FixedDatetime)

    today = date(2024, 1, 3)
    yesterday = date(2024, 1, 2)
    await fake_redis.set(f"rollup:demo:{yesterday.isoformat()}", 1)
    await fake_redis.set(f"rollup:demo:{today.isoformat()}", 1)

    if rollup_daily.rollup_runs_total:
        rollup_daily.rollup_runs_total._value.set(0)
    if rollup_daily.rollup_failures_total:
        rollup_daily.rollup_failures_total._value.set(0)

    await rollup_daily.main("demo")
    assert calls == []

    await fake_redis.delete(f"rollup:demo:{yesterday.isoformat()}")
    await fake_redis.delete(f"rollup:demo:{today.isoformat()}")
    await rollup_daily.main("demo")

    assert len(calls) == 2
    if rollup_daily.rollup_runs_total:
        assert rollup_daily.rollup_runs_total._value.get() == 2
    if rollup_daily.rollup_failures_total:
        assert rollup_daily.rollup_failures_total._value.get() == 0


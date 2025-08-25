import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import asyncio
import fakeredis.aioredis

from api.app.db import replica
from api.app.routes_metrics import db_replica_healthy
from api.app.main import app


def test_replica_fallback_and_metric():
    os.environ["READ_REPLICA_URL"] = "sqlite+aiosqlite:///./dev_replica.db"
    replica.READ_REPLICA_URL = os.environ["READ_REPLICA_URL"]
    replica._engine = None
    replica._sessionmaker = None
    replica._healthy = False
    app.state.redis = fakeredis.aioredis.FakeRedis()

    async def scenario():
        await replica.check_replica(app)
        assert app.state.replica_healthy is True
        assert db_replica_healthy._value.get() == 1

        async def fail_ping(engine):
            raise Exception("boom")

        replica._ping = fail_ping  # type: ignore
        await replica.check_replica(app)

        assert app.state.replica_healthy is False
        assert db_replica_healthy._value.get() == 0

        async with replica.replica_session() as session:
            assert str(session.bind.url).endswith("dev_master.db")

    asyncio.run(scenario())

import asyncio
import fnmatch
import os
import sys
import time
import types
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI

_webhooks_stub = types.ModuleType("routes_webhooks")
_webhooks_stub.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhooks", _webhooks_stub)

# stub missing services
sys.modules.setdefault("api.app.services.printer_watchdog", types.SimpleNamespace())

sys.path.append(str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("POSTGRES_MASTER_URL", "sqlite+aiosqlite:///./dev_master.db")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

import api.app.db as app_db

app_db.SessionLocal, app_db.engine = app_db.create_test_session()

try:  # pragma: no cover - fallback for broken app imports
    from api.app.main import app  # noqa: E402
except Exception:  # pragma: no cover
    app = FastAPI()


class DummyPipeline:
    def __init__(self, redis: "DummyRedis") -> None:
        self.redis = redis
        self.commands: list[tuple] = []

    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zcard(self, key):
        self.commands.append(("zcard", key))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        results = []
        for cmd in self.commands:
            name = cmd[0]
            if name == "zadd":
                await self.redis.zadd(cmd[1], cmd[2])
                results.append(None)
            elif name == "zremrangebyscore":
                await self.redis.zremrangebyscore(cmd[1], cmd[2], cmd[3])
                results.append(None)
            elif name == "zcard":
                results.append(await self.redis.zcard(cmd[1]))
            elif name == "expire":
                await self.redis.expire(cmd[1], cmd[2])
                results.append(None)
        self.commands.clear()
        return results


class DummyRedis:
    def __init__(self):
        self.store: dict[str, tuple[Any, float | None]] = {}
        self.sets: dict[str, set] = {}
        self.zsets: dict[str, list[tuple[int, str]]] = {}

    def _cleanup(self, key: str):
        val = self.store.get(key)
        if val and val[1] and val[1] < time.time():
            del self.store[key]
            return None
        return val

    async def sismember(self, name, member):
        if name == "blocklist:ip":
            return False
        return member in self.sets.get(name, set())

    async def sadd(self, name, *members):
        if name == "blocklist:ip":
            return 0
        s = self.sets.setdefault(name, set())
        before = len(s)
        s.update(members)
        return len(s) - before

    async def incr(self, key):
        val = self._cleanup(key)
        num = int(val[0]) if val else 0
        num += 1
        self.store[key] = (num, val[1] if val else None)
        return num

    async def set(self, key, value, ex=None):
        expire_at = time.time() + ex if ex else None
        self.store[key] = (value, expire_at)
        return True

    async def get(self, key):
        val = self._cleanup(key)
        return val[0] if val else None

    async def expire(self, key, seconds):
        val = self._cleanup(key)
        if val:
            self.store[key] = (val[0], time.time() + seconds)
            return True
        return False

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)
        return True

    async def setex(self, key, seconds, value):
        return await self.set(key, value, ex=seconds)

    async def exists(self, key):
        return 1 if self._cleanup(key) else 0

    async def ping(self):
        return True

    async def scan_iter(self, pattern: str):
        for key in list(self.store.keys()):
            if fnmatch.fnmatch(key, pattern):
                yield key

    async def zadd(self, key, mapping):
        zset = self.zsets.setdefault(key, [])
        for member, score in mapping.items():
            zset.append((score, member))
        return True

    async def zremrangebyscore(self, key, min_score, max_score):
        zset = self.zsets.get(key, [])
        self.zsets[key] = [
            item for item in zset if not (min_score <= item[0] <= max_score)
        ]
        return True

    async def zcard(self, key):
        return len(self.zsets.get(key, []))

    def pipeline(self):
        return DummyPipeline(self)

    def __getattr__(self, name):
        async def _dummy(*args, **kwargs):
            return None

        return _dummy


app.state.redis = DummyRedis()


@pytest.fixture(autouse=True)
def _event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def _safe_get_event_loop():
    try:
        return asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


asyncio.get_event_loop = _safe_get_event_loop


_orig_init = FastAPI.__init__


def _init(self, *args, **kwargs):
    _orig_init(self, *args, **kwargs)
    if not hasattr(self.state, "redis"):
        self.state.redis = DummyRedis()


FastAPI.__init__ = _init

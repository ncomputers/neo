import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI

sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.app.main import app  # noqa: E402


class DummyRedis:
    async def sismember(self, *args, **kwargs):
        return False

    async def incr(self, *args, **kwargs):
        return 0

    async def sadd(self, *args, **kwargs):
        return 0

    async def set(self, *args, **kwargs):
        return True

    async def get(self, *args, **kwargs):
        return None

    async def expire(self, *args, **kwargs):
        return True

    async def delete(self, *args, **kwargs):
        return True

    async def setex(self, *args, **kwargs):
        return True

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

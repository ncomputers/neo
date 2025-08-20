import asyncio
import pathlib
import sys

import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.security.blocklist import add_rejection, is_blocked, block_ip, clear_ip


def test_blocklist_helpers():
    redis = fakeredis.aioredis.FakeRedis()
    ip = "1.2.3.4"

    async def flow():
        assert await add_rejection(redis, ip) == 1
        assert await add_rejection(redis, ip) == 2
        assert not await is_blocked(redis, ip)
        await block_ip(redis, ip, ttl=10)
        assert await is_blocked(redis, ip)
        await clear_ip(redis, ip)
        assert not await is_blocked(redis, ip)
        assert await redis.exists(f"rej:ip:{ip}") == 0

    asyncio.run(flow())

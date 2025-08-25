"""Utilities to guard real-time connections (WebSocket/SSE).

This module centralises per-IP connection limits, heartbeat interval,
and backpressure handling for Server-Sent Events and WebSocket streams.
Environment variables provide tunables:
- ``MAX_CONN_PER_IP`` (default ``20``)
- ``HEARTBEAT_TIMEOUT_SEC`` (default ``30``)
- ``QUEUE_MAX`` (default ``100``)
"""

from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from starlette.websockets import WebSocket

MAX_CONN_PER_IP = int(os.getenv("MAX_CONN_PER_IP", "20"))
HEARTBEAT_TIMEOUT_SEC = int(os.getenv("HEARTBEAT_TIMEOUT_SEC", "30"))
QUEUE_MAX = int(os.getenv("QUEUE_MAX", "100"))

connections: dict[str, int] = defaultdict(int)


def register(ip: str) -> None:
    """Increment connection count for ``ip`` or raise ``HTTPException``."""
    if connections[ip] >= MAX_CONN_PER_IP:
        raise HTTPException(status_code=429, detail="RETRY")
    connections[ip] += 1


def unregister(ip: str) -> None:
    """Decrement connection count for ``ip``."""
    if connections[ip] > 0:
        connections[ip] -= 1


def queue(maxsize: int | None = None) -> asyncio.Queue[Any]:
    """Return an ``asyncio.Queue`` enforcing ``QUEUE_MAX`` by default."""
    return asyncio.Queue(maxsize=maxsize or QUEUE_MAX)


def heartbeat_task(websocket: WebSocket) -> asyncio.Task:
    """Return a task sending periodic pings to ``websocket``.

    The task stops silently when the connection drops. Consumers need not
    await the returned task but should cancel it on cleanup.
    """

    async def _hb() -> None:  # pragma: no cover - network timing
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_TIMEOUT_SEC)
                await websocket.send_json({"type": "ping"})
        except Exception:
            pass

    return asyncio.create_task(_hb())


async def push_or_drop(q: asyncio.Queue[Any], item: Any) -> None:
    """Enqueue ``item`` or raise ``HTTPException`` when ``q`` is full."""
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        await q.put(None)
        raise HTTPException(status_code=429, detail="RETRY")

# events.py

"""Simple in-memory Pub/Sub dispatcher with background consumer helpers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, List


class EventBus:
    """Dispatch events to subscribers via :class:`asyncio.Queue` instances."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, name: str) -> asyncio.Queue:
        """Register interest in ``name`` events and return a queue."""

        queue: asyncio.Queue = asyncio.Queue()
        self._subs[name].append(queue)
        return queue

    async def publish(self, name: str, payload: Dict[str, Any]) -> None:
        """Broadcast ``payload`` to all subscribers of ``name``."""

        for queue in self._subs.get(name, []):
            await queue.put(payload)


event_bus = EventBus()

# Stores for tests to introspect consumed events
ALERTS: list[dict] = []
EMA_UPDATES: list[dict] = []
REPORTS: list[dict] = []


async def alerts_sender(queue: asyncio.Queue) -> None:
    """Collect order alerts from the queue."""

    while True:
        ALERTS.append(await queue.get())


async def ema_updater(queue: asyncio.Queue) -> None:
    """Record payment verification events for EMA updates."""

    while True:
        EMA_UPDATES.append(await queue.get())


async def report_aggregator(queue: asyncio.Queue) -> None:
    """Aggregate table clean-up events."""

    while True:
        REPORTS.append(await queue.get())

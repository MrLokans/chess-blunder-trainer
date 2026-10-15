from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict

from blunder_tutor.events.event_types import Event, EventType

logger = logging.getLogger(__name__)

_DEBUG_EVENTS = os.environ.get("BLUNDER_TUTOR_DEBUG_EVENTS", "").lower() in (
    "1",
    "true",
    "yes",
)

if _DEBUG_EVENTS:
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[asyncio.Queue]] = defaultdict(list)
        self._all_subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: EventType | None = None) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            if event_type is None:
                self._all_subscribers.append(queue)
            else:
                self._subscribers[event_type].append(queue)

        return queue

    async def publish(self, event: Event) -> None:
        if _DEBUG_EVENTS:
            logger.debug("EventBus ← %s: %s", event.type.value, event.data)

        async with self._lock:
            queues = self._subscribers.get(event.type, []).copy()
            queues.extend(self._all_subscribers.copy())

        for queue in queues:
            # Queues are unbounded so put_nowait never blocks; no backpressure, accepted
            # (docs/quality/gaps.md).
            queue.put_nowait(event)

    async def unsubscribe(
        self, queue: asyncio.Queue, event_type: EventType | None = None
    ) -> None:
        async with self._lock:
            if event_type is None:
                if queue in self._all_subscribers:
                    self._all_subscribers.remove(queue)
            elif queue in self._subscribers[event_type]:
                self._subscribers[event_type].remove(queue)

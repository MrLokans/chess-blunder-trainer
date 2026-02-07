from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections import defaultdict

from .event_types import Event, EventType

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
    """In-memory async event bus for real-time updates.

    Uses asyncio.Queue for each subscriber to enable non-blocking
    event distribution. Thread-safe via asyncio locks.

    Set BLUNDER_TUTOR_DEBUG_EVENTS=1 to log every published event.
    """

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
            # If queue is full, skip this subscriber (they're not consuming fast enough)
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    async def unsubscribe(
        self, queue: asyncio.Queue, event_type: EventType | None = None
    ) -> None:
        async with self._lock:
            if event_type is None:
                if queue in self._all_subscribers:
                    self._all_subscribers.remove(queue)
            else:
                if queue in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(queue)

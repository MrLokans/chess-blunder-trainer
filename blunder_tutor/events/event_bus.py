from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict

from .event_types import Event, EventType


class EventBus:
    """In-memory async event bus for real-time updates.

    Uses asyncio.Queue for each subscriber to enable non-blocking
    event distribution. Thread-safe via asyncio locks.
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[asyncio.Queue]] = defaultdict(list)
        self._all_subscribers: list[asyncio.Queue] = []  # Subscribe to all events
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: EventType | None = None) -> asyncio.Queue:
        """Subscribe to an event type, returns a queue for receiving events.

        Args:
            event_type: Specific event type to subscribe to, or None for all events

        Returns:
            Queue that will receive events
        """
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            if event_type is None:
                self._all_subscribers.append(queue)
            else:
                self._subscribers[event_type].append(queue)

        return queue

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        async with self._lock:
            # Send to specific event type subscribers
            queues = self._subscribers.get(event.type, []).copy()
            # Also send to "all events" subscribers
            queues.extend(self._all_subscribers.copy())

        # Put event in all subscriber queues (outside lock)
        for queue in queues:
            # If queue is full, skip this subscriber (they're not consuming fast enough)
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    async def unsubscribe(
        self, queue: asyncio.Queue, event_type: EventType | None = None
    ) -> None:
        """Unsubscribe a queue from an event type.

        Args:
            queue: Queue to unsubscribe
            event_type: Event type to unsubscribe from, or None if subscribed to all
        """
        async with self._lock:
            if event_type is None:
                if queue in self._all_subscribers:
                    self._all_subscribers.remove(queue)
            else:
                if queue in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(queue)

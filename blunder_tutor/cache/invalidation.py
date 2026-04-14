from __future__ import annotations

import asyncio
import logging

from blunder_tutor.cache.backend import CacheBackend
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import CacheEvent, EventType

logger = logging.getLogger(__name__)

EVENT_TAG_MAPPING: dict[EventType, str] = {
    EventType.STATS_UPDATED: "stats",
    EventType.TRAPS_UPDATED: "traps",
    EventType.TRAINING_UPDATED: "training",
}


class CacheInvalidator:
    def __init__(self, cache: CacheBackend, event_bus: EventBus) -> None:
        self._cache = cache
        self._event_bus = event_bus
        self._running = False
        self._queues: list[tuple[EventType, asyncio.Queue]] = []

    async def start(self) -> None:
        self._running = True

        for event_type in EVENT_TAG_MAPPING:
            queue = await self._event_bus.subscribe(event_type)
            self._queues.append((event_type, queue))

        merged: asyncio.Queue = asyncio.Queue()

        async def _forward(source: asyncio.Queue) -> None:
            while self._running:
                try:
                    event = await source.get()
                    await merged.put(event)
                except asyncio.CancelledError:
                    raise

        tasks = [asyncio.create_task(_forward(q)) for _, q in self._queues]

        try:
            while self._running:
                try:
                    event = await merged.get()
                except asyncio.CancelledError:
                    raise

                tag_base = EVENT_TAG_MAPPING[event.type]
                user_key = event.data.get("user_key", "default")
                scoped_tag = f"{tag_base}:{user_key}"

                await self._cache.invalidate_tag(scoped_tag)
                logger.debug("Cache invalidated: %s", scoped_tag)

                cache_event = CacheEvent.create_cache_invalidated(tags=[scoped_tag])
                await self._event_bus.publish(cache_event)
        finally:
            for t in tasks:
                t.cancel()

    async def stop(self) -> None:
        self._running = False
        for event_type, queue in self._queues:
            await self._event_bus.unsubscribe(queue, event_type)
        self._queues.clear()

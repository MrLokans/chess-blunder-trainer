from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType

from blunder_tutor.cache.backend import CacheBackend
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import CacheEvent, Event, EventType

logger = logging.getLogger(__name__)

EVENT_TAG_MAPPING: MappingProxyType[EventType, str] = MappingProxyType(
    {
        EventType.STATS_UPDATED: "stats",
        EventType.TRAPS_UPDATED: "traps",
        EventType.TRAINING_UPDATED: "training",
        EventType.ELO_RATING_UPDATED: "elo_rating",
    }
)


class CacheInvalidator:
    def __init__(self, cache: CacheBackend, event_bus: EventBus) -> None:
        self._cache = cache
        self._event_bus = event_bus
        self._running = False
        self._queues: list[tuple[EventType, asyncio.Queue]] = []

    async def start(self) -> None:
        self._running = True
        merged, forwarders = await self._subscribe_and_fan_in()

        try:  # noqa: WPS501 — fire-and-forget forwarder tasks cancelled on shutdown; TaskGroup would re-raise inner exceptions, changing semantics.
            await self._consume_loop(merged)
        finally:
            for forwarder in forwarders:
                forwarder.cancel()

    async def stop(self) -> None:
        self._running = False
        for event_type, queue in self._queues:
            await self._event_bus.unsubscribe(queue, event_type)
        self._queues.clear()

    async def _subscribe_and_fan_in(
        self,
    ) -> tuple[asyncio.Queue, list[asyncio.Task]]:
        for event_type in EVENT_TAG_MAPPING:
            queue = await self._event_bus.subscribe(event_type)
            self._queues.append((event_type, queue))

        merged: asyncio.Queue = asyncio.Queue()

        async def _forward(source: asyncio.Queue) -> None:  # noqa: WPS430 — fan-in forwarder spawned per source queue; captures `self._running` and `merged`.
            while self._running:
                event = await source.get()
                await merged.put(event)

        forwarders = [asyncio.create_task(_forward(q)) for _, q in self._queues]
        return merged, forwarders

    async def _consume_loop(self, merged: asyncio.Queue) -> None:
        while self._running:
            event = await merged.get()
            await self._handle_event(event)

    async def _handle_event(self, event: Event) -> None:
        tag_base = EVENT_TAG_MAPPING[event.type]
        user_key = event.data.get("user_key", "default")
        scoped_tag = f"{tag_base}:{user_key}"

        await self._cache.invalidate_tag(scoped_tag)
        logger.debug("Cache invalidated: %s", scoped_tag)

        cache_event = CacheEvent.create_cache_invalidated(tags=[scoped_tag])
        await self._event_bus.publish(cache_event)

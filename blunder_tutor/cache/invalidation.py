from __future__ import annotations

import asyncio
import contextlib
import logging
from types import MappingProxyType

from blunder_tutor.cache.backend import CacheBackend
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import (
    SCOPE_KEY,
    CacheEvent,
    Event,
    EventType,
)

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
        self._queue: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Subscribe to the bus and spawn the consume task, then return.

        One all-events subscription (filtered on `EVENT_TAG_MAPPING`)
        replaces the per-type fan-in: no forwarder tasks, and the
        consume task is owned here so `stop()` can deterministically
        terminate it. The own-published `CACHE_INVALIDATED` event is not
        in the mapping, so the filter also breaks the feedback loop.
        """
        self._queue = await self._event_bus.subscribe()
        self._task = asyncio.create_task(self._consume_loop(self._queue))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._queue is not None:
            await self._event_bus.unsubscribe(self._queue)
            self._queue = None

    async def _consume_loop(self, queue: asyncio.Queue) -> None:
        while True:
            event = await queue.get()
            if event.type not in EVENT_TAG_MAPPING:
                continue
            try:
                await self._handle_event(event)
            except Exception:  # noqa: BLE001 — one bad event must not kill invalidation for the whole process; CancelledError (BaseException) still propagates so stop() stays deterministic.
                logger.exception(
                    "Cache invalidation failed for %s; continuing",
                    event.type.value,
                )

    async def _handle_event(self, event: Event) -> None:
        scope = event.data.get(SCOPE_KEY)
        if scope is None:
            logger.warning(
                "Skipping cache invalidation: %s event carries no scope",
                event.type.value,
            )
            return

        tag_base = EVENT_TAG_MAPPING[event.type]
        scoped_tag = f"{tag_base}:{scope}"

        await self._cache.invalidate_tag(scoped_tag)
        logger.debug("Cache invalidated: %s", scoped_tag)

        cache_event = CacheEvent.create_cache_invalidated(scope=scope, tags=[tag_base])
        await self._event_bus.publish(cache_event)

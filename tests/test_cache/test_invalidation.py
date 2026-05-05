from __future__ import annotations

import asyncio

import pytest

from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.invalidation import EVENT_TAG_MAPPING, CacheInvalidator
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import (
    EloRatingEvent,
    EventType,
    JobEvent,
    StatsEvent,
    TrainingEvent,
    TrapsEvent,
)


class TestCacheInvalidator:
    @pytest.fixture
    def event_bus(self) -> EventBus:
        return EventBus()

    @pytest.fixture
    def cache(self) -> InMemoryCacheBackend:
        return InMemoryCacheBackend()

    @pytest.fixture
    def invalidator(
        self, event_bus: EventBus, cache: InMemoryCacheBackend
    ) -> CacheInvalidator:
        return CacheInvalidator(cache=cache, event_bus=event_bus)

    async def _start_and_publish(
        self, invalidator: CacheInvalidator, event_bus: EventBus, event
    ):
        task = asyncio.create_task(invalidator.start())
        await asyncio.sleep(0.01)
        await event_bus.publish(event)
        await asyncio.sleep(0.05)
        await invalidator.stop()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_stats_updated_invalidates_stats_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"stats:alice"})
        await cache.set("k2", "v2", tags={"traps:alice"})
        event = StatsEvent.create_stats_updated(user_key="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_traps_updated_invalidates_traps_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"traps:bob"})
        await cache.set("k2", "v2", tags={"stats:bob"})
        event = TrapsEvent.create_traps_updated(user_key="bob")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_training_updated_invalidates_training_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"training:alice"})
        await cache.set("k2", "v2", tags={"stats:alice"})
        event = TrainingEvent.create_training_updated(user_key="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_elo_rating_updated_invalidates_elo_rating_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"elo_rating:alice"})
        await cache.set("k2", "v2", tags={"stats:alice"})
        event = EloRatingEvent.create_elo_rating_updated(
            user_key="alice", trigger="game_sync_completed"
        )
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_user_scoped_invalidation_only_affects_that_user(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"stats:alice"})
        await cache.set("k2", "v2", tags={"stats:bob"})
        event = StatsEvent.create_stats_updated(user_key="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_emits_cache_invalidated_event(self, invalidator, event_bus, cache):
        observer = await event_bus.subscribe(EventType.CACHE_INVALIDATED)
        await cache.set("k1", "v1", tags={"stats:alice"})
        event = StatsEvent.create_stats_updated(user_key="alice")
        task = asyncio.create_task(invalidator.start())
        await asyncio.sleep(0.01)
        await event_bus.publish(event)
        cache_event = await asyncio.wait_for(observer.get(), timeout=1.0)
        assert cache_event.type == EventType.CACHE_INVALIDATED
        assert "stats:alice" in cache_event.data["tags"]
        await invalidator.stop()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_unknown_event_is_ignored(self, invalidator, event_bus, cache):
        await cache.set("k1", "v1", tags={"stats:alice"})
        event = JobEvent.create_status_changed("job-1", "import", "pending")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") == "v1"

    async def test_missing_user_key_uses_default(self, invalidator, event_bus, cache):
        await cache.set("k1", "v1", tags={"stats:default"})
        event = StatsEvent.create_stats_updated()
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None

    async def test_stop_cancels_forwarder_tasks(self, invalidator, event_bus):
        tasks_before = set(asyncio.all_tasks())
        main_task = asyncio.create_task(invalidator.start())
        await asyncio.sleep(0.05)

        spawned = set(asyncio.all_tasks()) - tasks_before - {main_task}
        # One forwarder per subscribed event type (stats, traps, training).
        assert len(spawned) == len(EVENT_TAG_MAPPING)

        await invalidator.stop()
        main_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await main_task

        await asyncio.sleep(0.05)
        for forwarder in spawned:
            assert forwarder.done()

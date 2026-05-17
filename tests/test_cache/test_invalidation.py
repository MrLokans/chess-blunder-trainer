from __future__ import annotations

import asyncio

import pytest

from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.invalidation import CacheInvalidator
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import (
    EloRatingEvent,
    Event,
    EventType,
    JobEvent,
    StatsEvent,
    TrainingEvent,
    TrapsEvent,
)


class _RaiseOnceBackend(InMemoryCacheBackend):
    def __init__(self) -> None:
        super().__init__()
        self._raised = False

    async def invalidate_tag(self, tag: str) -> None:
        if not self._raised:
            self._raised = True
            msg = "transient backend failure"
            raise RuntimeError(msg)
        await super().invalidate_tag(tag)


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
        await invalidator.start()
        await event_bus.publish(event)
        await asyncio.sleep(0.05)
        await invalidator.stop()

    async def test_stats_updated_invalidates_stats_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"stats:alice"})
        await cache.set("k2", "v2", tags={"traps:alice"})
        event = StatsEvent.create_stats_updated(scope="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_traps_updated_invalidates_traps_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"traps:bob"})
        await cache.set("k2", "v2", tags={"stats:bob"})
        event = TrapsEvent.create_traps_updated(scope="bob")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_training_updated_invalidates_training_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"training:alice"})
        await cache.set("k2", "v2", tags={"stats:alice"})
        event = TrainingEvent.create_training_updated(scope="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_elo_rating_updated_invalidates_elo_rating_tag(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"elo_rating:alice"})
        await cache.set("k2", "v2", tags={"stats:alice"})
        event = EloRatingEvent.create_elo_rating_updated(
            scope="alice", trigger="game_sync_completed"
        )
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_user_scoped_invalidation_only_affects_that_user(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"stats:alice"})
        await cache.set("k2", "v2", tags={"stats:bob"})
        event = StatsEvent.create_stats_updated(scope="alice")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") is None
        assert await cache.get("k2") == "v2"

    async def test_emits_cache_invalidated_event(self, invalidator, event_bus, cache):
        observer = await event_bus.subscribe(EventType.CACHE_INVALIDATED)
        await cache.set("k1", "v1", tags={"stats:alice"})
        event = StatsEvent.create_stats_updated(scope="alice")
        await invalidator.start()
        await event_bus.publish(event)
        cache_event = await asyncio.wait_for(observer.get(), timeout=1.0)
        assert cache_event.type == EventType.CACHE_INVALIDATED
        # Carries the scope (so the WS layer can restrict delivery) and
        # only the LOGICAL tag — never another tenant's scoped key.
        assert cache_event.data["scope"] == "alice"
        assert cache_event.data["tags"] == ["stats"]
        assert "stats:alice" not in cache_event.data["tags"]
        await invalidator.stop()

    async def test_unknown_event_is_ignored(self, invalidator, event_bus, cache):
        await cache.set("k1", "v1", tags={"stats:alice"})
        event = JobEvent.create_status_changed("job-1", "import", "pending")
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") == "v1"

    async def test_missing_scope_skips_invalidation(
        self, invalidator, event_bus, cache
    ):
        await cache.set("k1", "v1", tags={"stats:alice"})
        await cache.set("k2", "v2", tags={"stats:default"})
        event = Event.create(EventType.STATS_UPDATED, {"trigger": "job_completed"})
        await self._start_and_publish(invalidator, event_bus, event)
        assert await cache.get("k1") == "v1"
        assert await cache.get("k2") == "v2"

    async def test_one_failing_event_does_not_kill_the_loop(self, event_bus):
        backend = _RaiseOnceBackend()
        invalidator = CacheInvalidator(cache=backend, event_bus=event_bus)
        await backend.set("a", "v", tags={"stats:alice"})
        await backend.set("b", "v", tags={"stats:bob"})

        await invalidator.start()
        await event_bus.publish(StatsEvent.create_stats_updated(scope="alice"))
        await asyncio.sleep(0.02)
        await event_bus.publish(StatsEvent.create_stats_updated(scope="bob"))
        await asyncio.sleep(0.05)

        # First event's invalidate_tag raised; the loop must survive and
        # still process the second event.
        assert await backend.get("a") == "v"
        assert await backend.get("b") is None
        assert invalidator._task is not None and not invalidator._task.done()
        await invalidator.stop()

    async def test_stop_terminates_consume_task_no_leak(self, invalidator, event_bus):
        tasks_before = set(asyncio.all_tasks())

        # start() subscribes and spawns the consume task, then returns
        # promptly (no fan-in, no forever-coroutine the caller must wrap).
        await asyncio.wait_for(invalidator.start(), timeout=1.0)
        spawned = set(asyncio.all_tasks()) - tasks_before
        assert len(spawned) == 1

        # stop() deterministically cancels-and-awaits the consume task;
        # the caller does NOT need an external cancel/CancelledError dance.
        await asyncio.wait_for(invalidator.stop(), timeout=1.0)
        await asyncio.sleep(0)
        assert not (set(asyncio.all_tasks()) - tasks_before)

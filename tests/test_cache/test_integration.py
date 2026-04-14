from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from fastapi import Request

from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.decorator import cached, set_cache_backend
from blunder_tutor.cache.invalidation import CacheInvalidator
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import StatsEvent, TrainingEvent, TrapsEvent


def _make_request(username: str = "testuser") -> Request:
    scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
    request = Request(scope)
    request.state.username = username
    return request


@dataclass
class MockFilter:
    start_date: str | None = None
    end_date: str | None = None


class TestCacheEndToEnd:
    @pytest.fixture
    def event_bus(self) -> EventBus:
        return EventBus()

    @pytest.fixture
    def cache(self) -> InMemoryCacheBackend:
        return InMemoryCacheBackend()

    @pytest.fixture(autouse=True)
    def _setup_backend(self, cache: InMemoryCacheBackend):
        set_cache_backend(cache)
        yield
        set_cache_backend(None)

    async def _run_with_invalidator(self, event_bus, cache, event):
        invalidator = CacheInvalidator(cache=cache, event_bus=event_bus)
        task = asyncio.create_task(invalidator.start())
        await asyncio.sleep(0.01)
        await event_bus.publish(event)
        await asyncio.sleep(0.05)
        await invalidator.stop()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_cached_endpoint_invalidated_by_event(self, event_bus, cache):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def get_stats(request: Request, filters: MockFilter) -> dict:
            nonlocal call_count
            call_count += 1
            return {"total": 42, "call": call_count}

        request = _make_request("alice")
        filters = MockFilter(start_date="2024-01-01")

        result1 = await get_stats(request=request, filters=filters)
        assert result1 == {"total": 42, "call": 1}
        result2 = await get_stats(request=request, filters=filters)
        assert result2 == {"total": 42, "call": 1}
        assert call_count == 1

        await self._run_with_invalidator(
            event_bus, cache, StatsEvent.create_stats_updated(user_key="alice")
        )

        result3 = await get_stats(request=request, filters=filters)
        assert result3["call"] == 2
        assert call_count == 2

    async def test_invalidation_does_not_affect_other_users(self, event_bus, cache):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def get_stats(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        alice_req = _make_request("alice")
        bob_req = _make_request("bob")

        await get_stats(request=alice_req)
        await get_stats(request=bob_req)
        assert call_count == 2

        await self._run_with_invalidator(
            event_bus, cache, StatsEvent.create_stats_updated(user_key="alice")
        )

        result_alice = await get_stats(request=alice_req)
        assert result_alice["call"] == 3
        result_bob = await get_stats(request=bob_req)
        assert result_bob["call"] == 2

    async def test_different_tags_independent(self, event_bus, cache):
        stats_calls = 0
        traps_calls = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def get_stats(request: Request) -> dict:
            nonlocal stats_calls
            stats_calls += 1
            return {"stats": stats_calls}

        @cached(tag="traps", ttl=300, version=1, key_params=[])
        async def get_traps(request: Request) -> dict:
            nonlocal traps_calls
            traps_calls += 1
            return {"traps": traps_calls}

        request = _make_request("alice")
        await get_stats(request=request)
        await get_traps(request=request)

        await self._run_with_invalidator(
            event_bus, cache, StatsEvent.create_stats_updated(user_key="alice")
        )

        await get_stats(request=request)
        assert stats_calls == 2
        await get_traps(request=request)
        assert traps_calls == 1

    async def test_training_event_invalidates_training_cache(self, event_bus, cache):
        call_count = 0

        @cached(tag="training", ttl=300, version=1, key_params=[])
        async def get_training(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        request = _make_request("alice")
        await get_training(request=request)
        assert call_count == 1

        await self._run_with_invalidator(
            event_bus, cache, TrainingEvent.create_training_updated(user_key="alice")
        )

        await get_training(request=request)
        assert call_count == 2

    async def test_traps_event_invalidates_traps_cache(self, event_bus, cache):
        call_count = 0

        @cached(tag="traps", ttl=300, version=1, key_params=[])
        async def get_traps(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        request = _make_request("alice")
        await get_traps(request=request)
        assert call_count == 1

        await self._run_with_invalidator(
            event_bus, cache, TrapsEvent.create_traps_updated(user_key="alice")
        )

        await get_traps(request=request)
        assert call_count == 2

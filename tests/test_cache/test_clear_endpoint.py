from __future__ import annotations

import asyncio
import types

import pytest
from fastapi import Request

from blunder_tutor.auth import UserContext, UserId, Username
from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.invalidation import CACHE_TAGS
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType
from blunder_tutor.web.api.cache import cache_router, clear_cache
from blunder_tutor.web.api.settings import delete_all_data
from blunder_tutor.web.dependencies import set_request_scope

# A real auth UUID (credentials mode) and the none-mode sentinel: the
# endpoint must behave identically for both.
_CREDENTIALS_SCOPE = "11111111-1111-1111-1111-111111111111"
_NONE_SCOPE = "_local"
_OTHER_SCOPE = "22222222-2222-2222-2222-222222222222"


def _make_request(scope: str, backend: InMemoryCacheBackend) -> Request:
    app = types.SimpleNamespace(state=types.SimpleNamespace(cache=backend))
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/cache/clear",
            "headers": [],
            "app": app,
        }
    )
    request.state.user_scope = scope
    return request


async def _seed_two_scopes(backend: InMemoryCacheBackend, scope: str) -> None:
    for tag in CACHE_TAGS:
        await backend.set(f"{scope}-{tag}", "v", tags={f"{tag}:{scope}"})
        await backend.set(f"other-{tag}", "v", tags={f"{tag}:{_OTHER_SCOPE}"})


class TestClearCacheEndpoint:
    def test_router_carries_scope_dependency(self) -> None:
        # Without set_request_scope the handler's request.state.user_scope
        # is never populated — scope resolution (identical in none and
        # credentials) is a property of the router, so lock it here.
        deps = [d.dependency for d in cache_router.dependencies]
        assert set_request_scope in deps

    @pytest.mark.parametrize("scope", [_NONE_SCOPE, _CREDENTIALS_SCOPE])
    async def test_clears_only_caller_scope_and_returns_cleared(
        self, scope: str
    ) -> None:
        backend = InMemoryCacheBackend()
        await _seed_two_scopes(backend, scope)
        request = _make_request(scope, backend)
        bus = EventBus()

        result = await clear_cache(request=request, event_bus=bus)

        assert sorted(result["cleared"]) == sorted(CACHE_TAGS)
        for tag in CACHE_TAGS:
            assert await backend.get(f"{scope}-{tag}") is None
            assert await backend.get(f"other-{tag}") == "v"

    @pytest.mark.parametrize("scope", [_NONE_SCOPE, _CREDENTIALS_SCOPE])
    async def test_publishes_scoped_cache_invalidated_event(self, scope: str) -> None:
        backend = InMemoryCacheBackend()
        await _seed_two_scopes(backend, scope)
        bus = EventBus()
        observer = await bus.subscribe(EventType.CACHE_INVALIDATED)

        await clear_cache(request=_make_request(scope, backend), event_bus=bus)

        event = await asyncio.wait_for(observer.get(), timeout=1.0)
        assert event.type == EventType.CACHE_INVALIDATED
        assert event.data["scope"] == scope
        # Logical tags only — never another tenant's scoped key.
        assert sorted(event.data["tags"]) == sorted(CACHE_TAGS)
        assert all(":" not in tag for tag in event.data["tags"])


class _StubJobService:
    async def create_job(self, job_type: str) -> str:
        return "job-123"


class TestDataWipeClearsCache:
    @pytest.mark.parametrize("scope", [_NONE_SCOPE, _CREDENTIALS_SCOPE])
    async def test_delete_all_data_also_clears_caller_cache(self, scope: str) -> None:
        backend = InMemoryCacheBackend()
        await _seed_two_scopes(backend, scope)
        request = _make_request(scope, backend)
        bus = EventBus()
        user_ctx = UserContext(
            user_id=UserId(scope),
            username=Username("tester"),
            session_token=None,
        )

        result = await delete_all_data(
            request=request,
            job_service=_StubJobService(),
            event_bus=bus,
            user_ctx=user_ctx,
        )

        assert result["job_id"] == "job-123"
        for tag in CACHE_TAGS:
            assert await backend.get(f"{scope}-{tag}") is None
            assert await backend.get(f"other-{tag}") == "v"

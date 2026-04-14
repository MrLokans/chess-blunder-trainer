from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import Request

from blunder_tutor.cache.backend import InMemoryCacheBackend, NullCacheBackend
from blunder_tutor.cache.decorator import (
    cached,
    get_cache_backend,
    resolve_user_key,
    set_cache_backend,
)


def _make_request(username: str = "testuser") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/stats",
        "headers": [],
    }
    request = Request(scope)
    request.state.username = username
    return request


class TestSetGetCacheBackend:
    def setup_method(self):
        set_cache_backend(None)

    def test_default_is_none(self):
        assert get_cache_backend() is None

    def test_set_and_get(self):
        backend = InMemoryCacheBackend()
        set_cache_backend(backend)
        assert get_cache_backend() is backend


class TestResolveUserKey:
    def test_returns_username_from_request_state(self):
        request = _make_request("alice")
        assert resolve_user_key(request) == "alice"

    def test_returns_default_when_no_username(self):
        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        request = Request(scope)
        assert resolve_user_key(request) == "default"


class TestCachedDecorator:
    @pytest.fixture(autouse=True)
    def _setup_cache(self):
        self.backend = InMemoryCacheBackend()
        set_cache_backend(self.backend)
        yield
        set_cache_backend(None)

    async def test_cache_miss_calls_function(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = _make_request()
        result = await my_endpoint(request=request, filters="all")
        assert result == {"result": "all"}
        assert call_count == 1

    async def test_cache_hit_skips_function(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = _make_request()
        await my_endpoint(request=request, filters="all")
        result = await my_endpoint(request=request, filters="all")
        assert result == {"result": "all"}
        assert call_count == 1

    async def test_different_params_different_cache_keys(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = _make_request()
        await my_endpoint(request=request, filters="all")
        await my_endpoint(request=request, filters="week")
        assert call_count == 2

    async def test_different_users_different_cache_keys(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        await my_endpoint(request=_make_request("alice"), filters="all")
        await my_endpoint(request=_make_request("bob"), filters="all")
        assert call_count == 2

    async def test_version_change_invalidates(self):
        call_count_v1 = 0
        call_count_v2 = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def endpoint_v1(request: Request) -> dict:
            nonlocal call_count_v1
            call_count_v1 += 1
            return {"version": 1}

        @cached(tag="stats", ttl=300, version=2, key_params=[])
        async def endpoint_v2(request: Request) -> dict:
            nonlocal call_count_v2
            call_count_v2 += 1
            return {"version": 2}

        request = _make_request()
        await endpoint_v1(request=request)
        await endpoint_v2(request=request)
        assert call_count_v1 == 1
        assert call_count_v2 == 1

    async def test_no_backend_calls_function_directly(self):
        set_cache_backend(None)
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = _make_request()
        await my_endpoint(request=request)
        await my_endpoint(request=request)
        assert call_count == 2

    async def test_null_backend_never_caches(self):
        set_cache_backend(NullCacheBackend())
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = _make_request()
        await my_endpoint(request=request)
        await my_endpoint(request=request)
        assert call_count == 2

    async def test_non_key_params_ignored_in_cache_key(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, repo: object, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = _make_request()
        repo1, repo2 = object(), object()
        await my_endpoint(request=request, repo=repo1, filters="all")
        await my_endpoint(request=request, repo=repo2, filters="all")
        assert call_count == 1

    async def test_tag_stored_with_user_scope(self):
        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            return {"ok": True}

        request = _make_request("alice")
        await my_endpoint(request=request)

        await self.backend.invalidate_tag("stats:alice")

        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint2(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        await my_endpoint2(request=request)
        assert call_count == 1

    async def test_dataclass_key_param(self):
        @dataclass
        class Filters:
            start: str | None = None
            end: str | None = None

        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: Filters) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = _make_request()
        f1 = Filters(start="2024-01-01", end="2024-12-31")
        f2 = Filters(start="2024-01-01", end="2024-12-31")
        f3 = Filters(start="2025-01-01")

        await my_endpoint(request=request, filters=f1)
        await my_endpoint(request=request, filters=f2)
        assert call_count == 1

        await my_endpoint(request=request, filters=f3)
        assert call_count == 2

    async def test_exception_propagates_and_result_not_cached(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def failing_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            msg = "db error"
            raise RuntimeError(msg)

        request = _make_request()

        with pytest.raises(RuntimeError, match="db error"):
            await failing_endpoint(request=request)
        assert call_count == 1

        with pytest.raises(RuntimeError, match="db error"):
            await failing_endpoint(request=request)
        assert call_count == 2

    async def test_none_return_value_is_cached(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def null_endpoint(request: Request) -> None:
            nonlocal call_count
            call_count += 1
            return None

        request = _make_request()
        result = await null_endpoint(request=request)
        assert result is None
        assert call_count == 1

        result = await null_endpoint(request=request)
        assert result is None
        assert call_count == 1

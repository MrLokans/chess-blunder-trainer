from __future__ import annotations

import types
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import Request

from blunder_tutor.cache.backend import InMemoryCacheBackend, NullCacheBackend
from blunder_tutor.cache.decorator import cached


def _make_app(backend: object, ttl: int = 300) -> object:
    return types.SimpleNamespace(
        state=types.SimpleNamespace(
            cache=backend,
            config=types.SimpleNamespace(cache=types.SimpleNamespace(default_ttl=ttl)),
        )
    )


def _make_request(
    scope: str = "testuser", *, backend: object, ttl: int = 300
) -> Request:
    asgi_scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/stats",
        "headers": [],
        "app": _make_app(backend, ttl),
    }
    request = Request(asgi_scope)
    request.state.user_scope = scope
    return request


class _RecordingBackend(InMemoryCacheBackend):
    def __init__(self) -> None:
        super().__init__()
        self.last_set_ttl: int | None = None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: set[str] | None = None,
    ) -> None:
        self.last_set_ttl = ttl
        await super().set(key, value, ttl=ttl, tags=tags)


class TestFailClosed:
    async def test_missing_request_raises(self):
        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(filters: str) -> dict:
            return {"result": filters}

        with pytest.raises(RuntimeError, match="Request"):
            await my_endpoint(filters="all")

    async def test_missing_user_scope_raises(self):
        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            return {"ok": True}

        asgi_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stats",
            "headers": [],
            "app": _make_app(InMemoryCacheBackend()),
        }
        request = Request(asgi_scope)  # no request.state.user_scope set

        with pytest.raises(RuntimeError, match="user_scope"):
            await my_endpoint(request=request)


class TestBackendFromAppState:
    async def test_backend_resolved_from_request_app_state(self):
        backend = InMemoryCacheBackend()
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = _make_request(backend=backend)
        await my_endpoint(request=request)
        await my_endpoint(request=request)
        assert call_count == 1

    async def test_distinct_app_backends_are_independent(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        await my_endpoint(request=_make_request(backend=InMemoryCacheBackend()))
        await my_endpoint(request=_make_request(backend=InMemoryCacheBackend()))
        assert call_count == 2

    async def test_null_backend_never_caches(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = _make_request(backend=NullCacheBackend())
        await my_endpoint(request=request)
        await my_endpoint(request=request)
        assert call_count == 2

    async def test_default_ttl_read_from_app_config(self):
        backend = _RecordingBackend()

        @cached(tag="stats", version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            return {"ok": True}

        await my_endpoint(request=_make_request(backend=backend, ttl=123))
        assert backend.last_set_ttl == 123

    async def test_explicit_ttl_overrides_app_config(self):
        backend = _RecordingBackend()

        @cached(tag="stats", ttl=999, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            return {"ok": True}

        await my_endpoint(request=_make_request(backend=backend, ttl=123))
        assert backend.last_set_ttl == 999


class TestCachedDecorator:
    @pytest.fixture(autouse=True)
    def _setup_cache(self):
        self.backend = InMemoryCacheBackend()

    def _request(self, scope: str = "testuser") -> Request:
        return _make_request(scope, backend=self.backend)

    async def test_cache_miss_calls_function(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        result = await my_endpoint(request=self._request(), filters="all")
        assert result == {"result": "all"}
        assert call_count == 1

    async def test_cache_hit_skips_function(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = self._request()
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

        request = self._request()
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

        await my_endpoint(request=self._request("alice"), filters="all")
        await my_endpoint(request=self._request("bob"), filters="all")
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

        request = self._request()
        await endpoint_v1(request=request)
        await endpoint_v2(request=request)
        assert call_count_v1 == 1
        assert call_count_v2 == 1

    async def test_non_key_params_ignored_in_cache_key(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=["filters"])
        async def my_endpoint(request: Request, repo: object, filters: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": filters}

        request = self._request()
        repo1, repo2 = object(), object()
        await my_endpoint(request=request, repo=repo1, filters="all")
        await my_endpoint(request=request, repo=repo2, filters="all")
        assert call_count == 1

    async def test_tag_stored_with_user_scope(self):
        call_count = 0

        @cached(tag="stats", ttl=300, version=1, key_params=[])
        async def my_endpoint(request: Request) -> dict:
            nonlocal call_count
            call_count += 1
            return {"ok": True}

        request = self._request("alice")
        await my_endpoint(request=request)
        await my_endpoint(request=request)
        assert call_count == 1

        await self.backend.invalidate_tag("stats:alice")

        await my_endpoint(request=request)
        assert call_count == 2

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

        request = self._request()
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

        request = self._request()

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

        request = self._request()
        result = await null_endpoint(request=request)
        assert result is None
        assert call_count == 1

        result = await null_endpoint(request=request)
        assert result is None
        assert call_count == 1

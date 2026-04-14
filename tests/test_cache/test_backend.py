from __future__ import annotations

import time as time_mod

import pytest

from blunder_tutor.cache.backend import InMemoryCacheBackend, NullCacheBackend


class TestInMemoryCacheBackend:
    @pytest.fixture
    def cache(self) -> InMemoryCacheBackend:
        return InMemoryCacheBackend()

    async def test_get_missing_key_returns_none(self, cache: InMemoryCacheBackend):
        assert await cache.get("nonexistent") is None

    async def test_set_and_get(self, cache: InMemoryCacheBackend):
        await cache.set("key1", {"data": 42})
        result = await cache.get("key1")
        assert result == {"data": 42}

    async def test_set_overwrites_existing(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "old")
        await cache.set("key1", "new")
        assert await cache.get("key1") == "new"

    async def test_delete_removes_entry(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "value")
        await cache.delete("key1")
        assert await cache.get("key1") is None

    async def test_delete_nonexistent_key_is_noop(self, cache: InMemoryCacheBackend):
        await cache.delete("nonexistent")

    async def test_ttl_expiry(
        self, cache: InMemoryCacheBackend, monkeypatch: pytest.MonkeyPatch
    ):
        current_time = 1000.0
        monkeypatch.setattr(time_mod, "monotonic", lambda: current_time)
        await cache.set("key1", "value", ttl=60)
        assert await cache.get("key1") == "value"
        current_time = 1061.0
        assert await cache.get("key1") is None

    async def test_no_ttl_never_expires(
        self, cache: InMemoryCacheBackend, monkeypatch: pytest.MonkeyPatch
    ):
        current_time = 1000.0
        monkeypatch.setattr(time_mod, "monotonic", lambda: current_time)
        await cache.set("key1", "value", ttl=None)
        current_time = 999999.0
        assert await cache.get("key1") == "value"

    async def test_set_with_tags(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "v1", tags={"stats:user1"})
        await cache.set("key2", "v2", tags={"stats:user1"})
        await cache.set("key3", "v3", tags={"traps:user1"})
        assert await cache.get("key1") == "v1"
        assert await cache.get("key2") == "v2"
        assert await cache.get("key3") == "v3"

    async def test_invalidate_tag_removes_tagged_entries(
        self, cache: InMemoryCacheBackend
    ):
        await cache.set("key1", "v1", tags={"stats:user1"})
        await cache.set("key2", "v2", tags={"stats:user1"})
        await cache.set("key3", "v3", tags={"traps:user1"})
        await cache.invalidate_tag("stats:user1")
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "v3"

    async def test_invalidate_tag_nonexistent_is_noop(
        self, cache: InMemoryCacheBackend
    ):
        await cache.invalidate_tag("nonexistent")

    async def test_invalidate_tag_cleans_tag_index(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "v1", tags={"stats:user1"})
        await cache.invalidate_tag("stats:user1")
        await cache.set("key2", "v2", tags={"stats:user1"})
        await cache.invalidate_tag("stats:user1")
        assert await cache.get("key2") is None

    async def test_entry_with_multiple_tags(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "v1", tags={"stats:user1", "dashboard:user1"})
        await cache.invalidate_tag("stats:user1")
        assert await cache.get("key1") is None

    async def test_clear_removes_everything(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "v1", tags={"stats:user1"})
        await cache.set("key2", "v2", tags={"traps:user1"})
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_clear_resets_tag_index(self, cache: InMemoryCacheBackend):
        await cache.set("key1", "v1", tags={"stats:user1"})
        await cache.clear()
        await cache.set("key1", "v1-new", tags={"stats:user1"})
        await cache.invalidate_tag("stats:user1")
        assert await cache.get("key1") is None


class TestNullCacheBackend:
    @pytest.fixture
    def cache(self) -> NullCacheBackend:
        return NullCacheBackend()

    async def test_get_always_returns_none(self, cache: NullCacheBackend):
        await cache.set("key1", "value")
        assert await cache.get("key1") is None

    async def test_delete_is_noop(self, cache: NullCacheBackend):
        await cache.delete("key1")

    async def test_invalidate_tag_is_noop(self, cache: NullCacheBackend):
        await cache.invalidate_tag("stats:user1")

    async def test_clear_is_noop(self, cache: NullCacheBackend):
        await cache.clear()

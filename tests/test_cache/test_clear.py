from __future__ import annotations

import pytest

from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.invalidation import (
    CACHE_TAGS,
    EVENT_TAG_MAPPING,
    clear_user_cache,
)


class _NoClearBackend(InMemoryCacheBackend):
    """Fails loudly if the tenant-isolation rule is violated.

    `clear()` wipes every tenant's entries in the shared in-memory
    backend; the per-user clear path must never reach for it.
    """

    async def clear(self) -> None:
        msg = "clear_user_cache must never call backend.clear()"
        raise AssertionError(msg)


class TestCacheTagsRegistry:
    def test_is_frozenset_of_expected_tags(self) -> None:
        assert isinstance(CACHE_TAGS, frozenset)
        assert sorted(CACHE_TAGS) == [
            "elo_rating",
            "stats",
            "training",
            "traps",
        ]

    def test_event_tag_mapping_values_drawn_from_registry(self) -> None:
        # Single source of truth: every EventType→tag value is a member,
        # and together they cover the whole registry.
        assert set(EVENT_TAG_MAPPING.values()) == CACHE_TAGS


class TestClearUserCache:
    @pytest.fixture
    def cache(self) -> InMemoryCacheBackend:
        return InMemoryCacheBackend()

    async def test_invalidates_every_registered_tag_for_scope(
        self, cache: InMemoryCacheBackend
    ) -> None:
        for tag in CACHE_TAGS:
            await cache.set(f"k-{tag}", "v", tags={f"{tag}:alice"})

        await clear_user_cache(cache, "alice")

        for tag in CACHE_TAGS:
            assert await cache.get(f"k-{tag}") is None

    async def test_other_scope_entries_survive(
        self, cache: InMemoryCacheBackend
    ) -> None:
        await cache.set("alice-stats", "v", tags={"stats:alice"})
        await cache.set("bob-stats", "v", tags={"stats:bob"})
        await cache.set("bob-traps", "v", tags={"traps:bob"})

        await clear_user_cache(cache, "alice")

        assert await cache.get("alice-stats") is None
        assert await cache.get("bob-stats") == "v"
        assert await cache.get("bob-traps") == "v"

    async def test_returns_cleared_tag_list(self, cache: InMemoryCacheBackend) -> None:
        cleared = await clear_user_cache(cache, "alice")

        assert isinstance(cleared, list)
        # Exactly once per registered tag — frozenset order is unspecified
        # so compare as multisets, not an ordered literal.
        assert sorted(cleared) == sorted(CACHE_TAGS)

    async def test_never_calls_backend_clear(self) -> None:
        backend = _NoClearBackend()
        await backend.set("alice-stats", "v", tags={"stats:alice"})

        await clear_user_cache(backend, "alice")

        assert await backend.get("alice-stats") is None

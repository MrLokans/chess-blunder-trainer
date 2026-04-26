from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(
        self, key: str, value: Any, ttl: int | None = None, tags: set[str] | None = None
    ) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def invalidate_tag(self, tag: str) -> None: ...
    async def clear(self) -> None: ...


@dataclass
class _CacheEntry:
    value: Any
    created_at: float
    ttl: int | None

    @property
    def expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.monotonic() - self.created_at > self.ttl


class InMemoryCacheBackend:
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._tag_index: dict[str, set[str]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expired:
            self._remove_key(key)
            return None
        return entry.value

    async def set(
        self, key: str, value: Any, ttl: int | None = None, tags: set[str] | None = None
    ) -> None:
        if key in self._store:
            self._remove_key_from_tags(key)
        self._store[key] = _CacheEntry(
            value=value, created_at=time.monotonic(), ttl=ttl
        )
        if tags:
            for tag in tags:
                self._tag_index.setdefault(tag, set()).add(key)

    async def delete(self, key: str) -> None:
        self._remove_key(key)

    async def invalidate_tag(self, tag: str) -> None:
        keys = self._tag_index.pop(tag, set())
        for key in keys:
            self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
        self._tag_index.clear()

    def _remove_key(self, key: str) -> None:
        self._store.pop(key, None)
        self._remove_key_from_tags(key)

    def _remove_key_from_tags(self, key: str) -> None:
        for tag_keys in self._tag_index.values():
            tag_keys.discard(key)


class NullCacheBackend:
    """No-op backend: every `get` misses, every write is dropped."""

    async def get(self, key: str) -> Any | None:
        pass

    async def set(
        self, key: str, value: Any, ttl: int | None = None, tags: set[str] | None = None
    ) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def invalidate_tag(self, tag: str) -> None:
        pass

    async def clear(self) -> None:
        pass

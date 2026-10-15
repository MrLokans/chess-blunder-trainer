from __future__ import annotations


class PerUserCache[V]:
    """No bulk clear by design: a privilege change must invalidate exactly its own keys."""

    def __init__(self) -> None:
        self._entries: dict[str, V] = {}

    def get(self, key: str) -> V | None:
        return self._entries.get(key)

    def set(self, key: str, value: V) -> None:
        self._entries[key] = value

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

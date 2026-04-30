from __future__ import annotations


class PerUserCache[V]:
    """App-level cache keyed by `user_id` (or the `_local` sentinel in
    `AUTH_MODE=none`). Encapsulates the dict so callers cannot leak state
    across users by reaching into the wrong key — the Phase-3 review
    fix-shape made permanent.

    Reads return `None` on miss; callers handle the fallback. There is no
    bulk-clear API by design: a privilege change must invalidate exactly
    the keys it owns.
    """

    def __init__(self) -> None:
        self._entries: dict[str, V] = {}

    def get(self, key: str) -> V | None:
        return self._entries.get(key)

    def set(self, key: str, value: V) -> None:
        self._entries[key] = value

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

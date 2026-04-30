from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class FetchState:
    """Shared mutable state for paginated fetchers.

    Both Chess.com and Lichess fetch loops accumulate games + dedupe IDs,
    decrement a remaining-quota counter, and emit progress callbacks. This
    bundles those into one passable object so the inner-loop helpers don't
    take 8+ args each.
    """

    max_games: int | None
    progress_callback: Callable[[int, int], Awaitable[None]] | None
    games: list[dict[str, object]] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    remaining: int | None = field(init=False)

    def __post_init__(self) -> None:
        self.remaining = self.max_games

    def tick_remaining(self) -> bool:
        """Decrement remaining; return True iff the quota is now exhausted."""
        if self.remaining is None:
            return False
        self.remaining -= 1
        return self.remaining <= 0

    async def report_progress(self) -> None:
        if self.progress_callback is None:
            return
        await self.progress_callback(
            len(self.games),
            self.max_games or len(self.games),
        )

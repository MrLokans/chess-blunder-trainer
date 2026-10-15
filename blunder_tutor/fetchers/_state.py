from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class FetchState:
    max_games: int | None
    progress_callback: Callable[[int, int], Awaitable[None]] | None
    games: list[dict[str, object]] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    remaining: int | None = field(init=False)

    def __post_init__(self) -> None:
        self.remaining = self.max_games

    def tick_remaining(self) -> bool:
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

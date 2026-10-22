from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from blunder_tutor.events.event_types import SCOPE_KEY, Event, EventType

# Only the latest per key matters within a window. Discrete events (job.status_changed,
# job.completed, cache.invalidated) pass through: each carries independent meaning.
COALESCED_TYPES: frozenset[EventType] = frozenset(
    (
        EventType.STATS_UPDATED,
        EventType.JOB_PROGRESS_UPDATED,
        EventType.TRAPS_UPDATED,
        EventType.TRAINING_UPDATED,
    )
)

FlushFn = Callable[[Event], Awaitable[None]]


def _coalesce_key(event: Event) -> tuple[str | None, EventType]:
    # Defensive: every COALESCED_TYPES factory sets its key, but a scope-less one would
    # collapse across tenants rather than raise.
    data = event.data if isinstance(event.data, dict) else {}
    if event.type is EventType.JOB_PROGRESS_UPDATED:
        # Key on job_id so one user's concurrent jobs don't collapse into one broadcast.
        return (data.get("job_id"), event.type)
    return (data.get(SCOPE_KEY), event.type)


class CoalescingBroadcaster:
    """Latest-wins per `(scope, type)`; pass-through types and `window_ms<=0` flush
    immediately."""

    def __init__(self, flush: FlushFn, window_ms: int) -> None:
        self._flush = flush
        self._window = window_ms / 1000
        self._pending: dict[tuple[str | None, EventType], Event] = {}
        self._flush_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def submit(self, event: Event) -> None:
        if self._window <= 0 or event.type not in COALESCED_TYPES:
            await self._flush(event)
            return
        async with self._lock:
            self._pending[_coalesce_key(event)] = event
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._flush_after())

    async def aclose(self) -> None:
        task = self._flush_task
        self._flush_task = None
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _flush_after(self) -> None:
        await asyncio.sleep(self._window)
        async with self._lock:
            pending = self._pending
            self._pending = {}
        for event in pending.values():
            await self._flush(event)
        async with self._lock:
            # Events parked while the broadcast loop ran had no timer (this task wasn't
            # `.done()` yet); re-arm under `submit`'s lock so a burst's last event isn't
            # stranded.
            if self._pending:
                self._flush_task = asyncio.create_task(self._flush_after())
            else:
                self._flush_task = None

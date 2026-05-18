from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from blunder_tutor.events.event_types import SCOPE_KEY, Event, EventType

# High-frequency "current state, refetch if interested" events: only the
# latest per key matters within a window. Terminal/discrete events
# (job.status_changed, job.completed, cache.invalidated) are NOT here —
# each occurrence carries independent meaning and passes straight through.
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
    # Every COALESCED_TYPES factory in event_types.py guarantees its key
    # field (SCOPE_KEY for stats/traps/training, job_id for progress), so
    # the `None` fallback is unreachable today. Kept defensive: a future
    # scope-less factory would collapse cross-tenant rather than raise —
    # a regression a reader of this function must see coming.
    data = event.data if isinstance(event.data, dict) else {}
    if event.type is EventType.JOB_PROGRESS_UPDATED:
        # Progress carries no scope; collapsing two concurrent jobs into
        # one broadcast would lose information, so key on job_id.
        return (data.get("job_id"), event.type)
    return (data.get(SCOPE_KEY), event.type)


class CoalescingBroadcaster:
    """Latest-wins, per-`(scope, type)` event coalescer for WS broadcast.

    Sits between the broadcast queue loop and the flush callback. A burst
    of N coalesced events for one key inside `window_ms` produces a single
    flush carrying the last payload. Pass-through types and `window_ms<=0`
    flush immediately, making the un-coalesced path a strict subset.
    """

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
            # Events submitted while the broadcast loop ran above were
            # parked with no timer: this task was not yet `.done()`, so
            # `submit`'s re-arm check passed them over. Re-arm here, under
            # the same lock `submit` uses, so the last event of a burst is
            # never stranded waiting for an unrelated future submit.
            if self._pending:
                self._flush_task = asyncio.create_task(self._flush_after())
            else:
                self._flush_task = None

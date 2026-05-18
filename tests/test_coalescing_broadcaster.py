from __future__ import annotations

import asyncio

from blunder_tutor.events.coalescing import CoalescingBroadcaster
from blunder_tutor.events.event_types import Event, EventType

# Small window with a generous (5x) wait margin: under `-n auto` CPU
# contention `asyncio.sleep` overshoots by tens of ms, so assertions key
# on "much longer than the window has elapsed", never on a tight edge.
_WINDOW_MS = 20
_PAST_WINDOW = _WINDOW_MS * 5 / 1000


def _stats(scope: str, n: int) -> Event:
    return Event.create(EventType.STATS_UPDATED, {"scope": scope, "n": n})


def _progress(job_id: str, current: int) -> Event:
    return Event.create(
        EventType.JOB_PROGRESS_UPDATED,
        {"job_id": job_id, "job_type": "analyze", "current": current},
    )


def _status(job_id: str, status: str) -> Event:
    return Event.create(
        EventType.JOB_STATUS_CHANGED, {"job_id": job_id, "status": status}
    )


class _Sink:
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def __call__(self, event: Event) -> None:
        self.events.append(event)


class TestCoalescing:
    async def test_burst_for_one_scope_flushes_once_with_last_payload(self) -> None:
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=_WINDOW_MS)

        for i in range(100):
            await broadcaster.submit(_stats("u1", i))

        assert sink.events == []  # synchronous burst; flush needs the timer
        await asyncio.sleep(_PAST_WINDOW)

        assert len(sink.events) == 1
        assert sink.events[0].data["n"] == 99

    async def test_burst_across_scopes_flushes_once_per_scope(self) -> None:
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=_WINDOW_MS)

        for scope in ("u1", "u2", "u3"):
            for i in range(10):
                await broadcaster.submit(_stats(scope, i))

        await asyncio.sleep(_PAST_WINDOW)

        assert len(sink.events) == 3
        by_scope = {e.data["scope"]: e.data["n"] for e in sink.events}
        assert by_scope == {"u1": 9, "u2": 9, "u3": 9}

    async def test_pass_through_event_flushes_immediately(self) -> None:
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=_WINDOW_MS)

        await broadcaster.submit(_stats("u1", 0))  # buffered
        await broadcaster.submit(_status("j1", "succeeded"))  # terminal

        assert [e.type for e in sink.events] == [EventType.JOB_STATUS_CHANGED]

    async def test_window_zero_flushes_every_event_immediately(self) -> None:
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=0)

        for i in range(5):
            await broadcaster.submit(_stats("u1", i))

        assert [e.data["n"] for e in sink.events] == [0, 1, 2, 3, 4]

    async def test_progress_keyed_by_job_id_not_scope(self) -> None:
        # Spike correction: progress has no scope; two concurrent jobs
        # must not collapse into one broadcast.
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=_WINDOW_MS)

        for i in range(10):
            await broadcaster.submit(_progress("jobA", i))
            await broadcaster.submit(_progress("jobB", i))

        await asyncio.sleep(_PAST_WINDOW)

        assert len(sink.events) == 2
        by_job = {e.data["job_id"]: e.data["current"] for e in sink.events}
        assert by_job == {"jobA": 9, "jobB": 9}

    async def test_terminal_event_during_in_flight_flush_not_stranded(self) -> None:
        # Regression: an event submitted while a prior flush is still
        # broadcasting must not be parked with no armed timer. If it is
        # the last event of a burst, it would otherwise never be flushed.
        release = asyncio.Event()
        started = asyncio.Event()
        flushed: list[Event] = []

        async def slow_flush(event: Event) -> None:
            flushed.append(event)
            started.set()
            await release.wait()  # hold the broadcast in-flight

        broadcaster = CoalescingBroadcaster(flush=slow_flush, window_ms=20)

        await broadcaster.submit(_stats("u1", 0))
        await started.wait()  # first flush is now in-flight (blocked)

        await broadcaster.submit(_stats("u1", 1))  # terminal event arrives
        release.set()  # let the in-flight flush complete

        await asyncio.sleep(0.1)  # ample time for a re-armed window

        assert [e.data["n"] for e in flushed] == [0, 1]

    async def test_re_arms_for_event_after_a_completed_flush(self) -> None:
        # A second burst that arrives only after the first window's flush
        # has fired must get its own flush, not be dropped.
        sink = _Sink()
        broadcaster = CoalescingBroadcaster(flush=sink, window_ms=_WINDOW_MS)

        await broadcaster.submit(_stats("u1", 0))
        await asyncio.sleep(_PAST_WINDOW)
        assert [e.data["n"] for e in sink.events] == [0]

        await broadcaster.submit(_stats("u1", 1))
        await asyncio.sleep(_PAST_WINDOW)
        assert [e.data["n"] for e in sink.events] == [0, 1]

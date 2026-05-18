import asyncio
import contextlib

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import Event, EventType, StatsEvent
from blunder_tutor.events.websocket_manager import ConnectionManager


def test_websocket_connection(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe to job events
        websocket.send_json({"action": "subscribe", "events": ["job.created"]})

        # Should receive subscription confirmation
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert "job.created" in response["events"]


def test_websocket_ping_pong(app):
    with app.websocket_connect("/ws") as websocket:
        # Send ping
        websocket.send_json({"action": "ping"})

        # Should receive pong
        response = websocket.receive_json()
        assert response["type"] == "pong"


def test_websocket_multiple_subscriptions(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe to multiple events
        websocket.send_json(
            {
                "action": "subscribe",
                "events": ["job.created", "job.status_changed", "stats.updated"],
            }
        )

        # Should receive confirmation with all events
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert "job.created" in response["events"]
        assert "job.status_changed" in response["events"]
        assert "stats.updated" in response["events"]


def test_websocket_invalid_event_type(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe with some invalid event types
        websocket.send_json(
            {
                "action": "subscribe",
                "events": ["job.created", "invalid.event.type", "job.completed"],
            }
        )

        # Should still receive confirmation (invalid types are skipped)
        response = websocket.receive_json()
        assert response["type"] == "subscribed"


def test_none_mode_delivers_scoped_event_regardless_of_user(app):
    # Back-compat lock for AUTH_MODE=none: connections without a user_id
    # see every event, even ones tagged with a scope. Single-user
    # instance, no cross-user leak possible by construction.
    with app.websocket_connect("/ws") as websocket:
        websocket.send_json({"action": "subscribe", "events": ["stats.updated"]})
        assert websocket.receive_json()["type"] == "subscribed"

        connection_manager = app.app.state.connection_manager
        app.portal.call(
            connection_manager.broadcast_event,
            StatsEvent.create_stats_updated(scope="some-user-id"),
        )
        message = websocket.receive_json()

    assert message["type"] == "stats.updated"
    assert message["data"]["scope"] == "some-user-id"


_WINDOW_MS = 20
_PAST_WINDOW = _WINDOW_MS * 5 / 1000  # 5x margin: robust under -n auto load


class TestCoalescingIntegration:
    async def _start(
        self, cm: ConnectionManager
    ) -> tuple[list[Event], asyncio.Task[None]]:
        sent: list[Event] = []

        async def record(event: Event) -> None:
            sent.append(event)

        cm.broadcast_event = record  # type: ignore[method-assign]
        task = asyncio.create_task(cm.start_broadcasting())
        await asyncio.sleep(0)  # let start_broadcasting subscribe
        return sent, task

    async def _stop(self, task: asyncio.Task[None]) -> None:
        # Cancelling the loop runs its `finally`, which `aclose()`s the
        # coalescer so no flush timer is GC'd as an orphan pending task.
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_burst_through_bus_coalesces_to_one_broadcast(self) -> None:
        bus = EventBus()
        cm = ConnectionManager(bus, coalesce_window_ms=_WINDOW_MS)
        sent, task = await self._start(cm)

        for i in range(50):
            await bus.publish(
                Event.create(EventType.STATS_UPDATED, {"scope": "u1", "n": i})
            )
        await asyncio.sleep(_PAST_WINDOW)
        await self._stop(task)

        assert len(sent) == 1
        assert sent[0].data["n"] == 49

    async def test_window_zero_preserves_un_coalesced_delivery(self) -> None:
        bus = EventBus()
        cm = ConnectionManager(bus, coalesce_window_ms=0)
        sent, task = await self._start(cm)

        for i in range(5):
            await bus.publish(
                Event.create(EventType.STATS_UPDATED, {"scope": "u1", "n": i})
            )
        # window 0 → immediate pass-through; yield until the loop drains
        # the queue rather than sleeping a fixed wall-clock interval.
        for _ in range(20):
            await asyncio.sleep(0)
            if len(sent) == 5:
                break
        await self._stop(task)

        assert [e.data["n"] for e in sent] == [0, 1, 2, 3, 4]

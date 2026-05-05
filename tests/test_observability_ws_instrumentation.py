"""Smoke test: WebSocket connection lifecycle emits the documented
counters and active-connection gauge with bounded-cardinality tags.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from blunder_tutor.events import websocket_manager as ws_module
from blunder_tutor.events.event_types import Event, EventType
from blunder_tutor.events.websocket_manager import ConnectionManager
from tests.helpers.observability import FacadeCallRecorder, patch_facade


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> FacadeCallRecorder:
    return patch_facade(monkeypatch, ws_module)


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


def _make_event(event_type: EventType) -> Event:
    return Event(type=event_type, data={}, timestamp="2026-01-01T00:00:00Z")


class TestWebSocketLifecycleInstrumentation:
    async def test_connect_emits_open_count_and_active_gauge(
        self, recorder: FacadeCallRecorder
    ) -> None:
        manager = ConnectionManager(event_bus=MagicMock())
        await manager.connect(_make_ws())

        opens = [c for c in recorder.counts if c["name"] == "ws.connection.opened"]
        assert opens == [{"name": "ws.connection.opened", "value": 1.0, "tags": None}]

        actives = [g for g in recorder.gauges if g["name"] == "ws.connections.active"]
        assert actives == [{"name": "ws.connections.active", "value": 1, "tags": None}]

    async def test_disconnect_emits_close_count_with_default_reason(
        self, recorder: FacadeCallRecorder
    ) -> None:
        manager = ConnectionManager(event_bus=MagicMock())
        conn_id = await manager.connect(_make_ws())
        await manager.disconnect(conn_id)

        closes = [c for c in recorder.counts if c["name"] == "ws.connection.closed"]
        assert closes == [
            {
                "name": "ws.connection.closed",
                "value": 1.0,
                "tags": {"reason": "client_close"},
            }
        ]

        actives = [g for g in recorder.gauges if g["name"] == "ws.connections.active"]
        assert actives[-1]["value"] == 0

    async def test_disconnect_propagates_explicit_reason(
        self, recorder: FacadeCallRecorder
    ) -> None:
        manager = ConnectionManager(event_bus=MagicMock())
        conn_id = await manager.connect(_make_ws())
        await manager.disconnect(conn_id, reason="error")

        closes = [c for c in recorder.counts if c["name"] == "ws.connection.closed"]
        assert closes[0]["tags"] == {"reason": "error"}

    async def test_broadcast_emits_per_event_type_count(
        self, recorder: FacadeCallRecorder
    ) -> None:
        manager = ConnectionManager(event_bus=MagicMock())
        await manager.broadcast_event(_make_event(EventType.JOB_COMPLETED))

        broadcasts = [c for c in recorder.counts if c["name"] == "ws.broadcast.sent"]
        assert broadcasts == [
            {
                "name": "ws.broadcast.sent",
                "value": 1.0,
                "tags": {"event_type": "job.completed"},
            }
        ]

    async def test_broadcast_failure_disconnect_uses_send_failed_reason(
        self, recorder: FacadeCallRecorder
    ) -> None:
        manager = ConnectionManager(event_bus=MagicMock())
        ws = _make_ws()
        ws.send_json = AsyncMock(side_effect=RuntimeError("dead pipe"))
        conn_id = await manager.connect(ws)
        await manager.subscribe(conn_id, [EventType.JOB_COMPLETED.value])

        await manager.broadcast_event(_make_event(EventType.JOB_COMPLETED))

        closes = [c for c in recorder.counts if c["name"] == "ws.connection.closed"]
        assert len(closes) == 1
        assert closes[0]["tags"] == {"reason": "send_failed"}

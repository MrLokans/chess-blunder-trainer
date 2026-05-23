from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import uuid

from fastapi import WebSocket

from blunder_tutor.auth import UserId
from blunder_tutor.events.coalescing import CoalescingBroadcaster
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import SCOPE_KEY, Event, EventType
from blunder_tutor.observability import count, gauge

log = logging.getLogger(__name__)

_DEFAULT_COALESCE_WINDOW_MS = 500


def _event_target_user(event: Event) -> str | None:
    return event.data.get(SCOPE_KEY) if isinstance(event.data, dict) else None


def _default_coalesce_window_ms() -> int:
    raw = os.environ.get("EVENT_COALESCE_WINDOW_MS")
    if not raw:
        return _DEFAULT_COALESCE_WINDOW_MS
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_COALESCE_WINDOW_MS


class ConnectionManager:
    def __init__(self, event_bus: EventBus, *, coalesce_window_ms: int | None = None):
        self.event_bus = event_bus
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_subscriptions: dict[str, set[EventType]] = {}
        self.connection_user_ids: dict[str, UserId | None] = {}
        self._coalesce_window_ms = (
            _default_coalesce_window_ms()
            if coalesce_window_ms is None
            else coalesce_window_ms
        )

    async def connect(
        self, websocket: WebSocket, *, user_id: UserId | None = None
    ) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_subscriptions[connection_id] = set()
        self.connection_user_ids[connection_id] = user_id
        count("ws.connection.opened")
        gauge("ws.connections.active", len(self.active_connections))
        return connection_id

    async def disconnect(
        self, connection_id: str, reason: str = "client_close"
    ) -> None:
        self.active_connections.pop(connection_id, None)
        self.connection_subscriptions.pop(connection_id, None)
        self.connection_user_ids.pop(connection_id, None)
        count("ws.connection.closed", tags={"reason": reason})
        gauge("ws.connections.active", len(self.active_connections))

    async def subscribe(self, connection_id: str, event_types: list[str]) -> None:
        subscriptions = self.connection_subscriptions.get(connection_id)
        if subscriptions is None:
            return
        for event_type_str in event_types:
            # Skip strings that don't map to a known EventType.
            with contextlib.suppress(ValueError):
                subscriptions.add(EventType(event_type_str))

    async def broadcast_event(self, event: Event) -> None:
        try:
            message = event.to_dict()
            target_user = _event_target_user(event)
        except Exception:
            # A single un-serializable event must be dropped, not allowed
            # to propagate: it would kill the broadcast loop and stop all
            # WS delivery for the process lifetime.
            log.exception("Dropping un-broadcastable event type=%s", event.type)
            count("ws.broadcast.error", tags={"stage": "prepare"})
            return
        count("ws.broadcast.sent", tags={"event_type": event.type.value})
        disconnected: list[str] = []
        for conn_id, ws in list(self.active_connections.items()):
            try:
                deliver = self._should_deliver(conn_id, event.type, target_user)
            except Exception:
                # A delivery-check failure for one connection must not
                # starve the others, so isolate it per connection.
                log.exception("Delivery check failed for connection %s", conn_id)
                count("ws.broadcast.error", tags={"stage": "should_deliver"})
                continue
            if not deliver:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(conn_id)
        for conn_id in disconnected:
            await self.disconnect(conn_id, reason="send_failed")

    async def start_broadcasting(self) -> None:
        queue = await self.event_bus.subscribe(event_type=None)
        coalescer = CoalescingBroadcaster(
            flush=self.broadcast_event, window_ms=self._coalesce_window_ms
        )
        try:  # noqa: WPS501 — bare try/finally is intentional: the loop never returns normally; cleanup runs only on cancellation.
            await self._consume(queue, coalescer)
        finally:
            # Drop any pending coalesced events (a reconnecting client
            # refetches anyway) but cancel the in-flight flush timer so it
            # is not GC'd as an orphaned pending task.
            await coalescer.aclose()

    async def _consume(
        self, queue: asyncio.Queue, coalescer: CoalescingBroadcaster
    ) -> None:
        while True:
            event = await queue.get()
            try:
                await coalescer.submit(event)
            except Exception:
                # Backstop the per-event guards in broadcast_event: any leak
                # from the submit/flush path must drop one event, never end
                # the loop (a silent total-outage SPOF). CancelledError is a
                # BaseException and still propagates to start_broadcasting's
                # finally so the coalescer is closed on shutdown.
                log.exception("Broadcast submit failed; dropping event")
                count("ws.broadcast.error", tags={"stage": "submit"})

    def _should_deliver(
        self, conn_id: str, event_type: EventType, target_user: str | None
    ) -> bool:
        # When an event carries a scope, deliver only to connections
        # authenticated as that user. Job-lifecycle events carry no scope
        # and still broadcast to all subscribers — per-user scoping of
        # those is a separate, untracked concern, not part of the
        # coalescing work. Connections without a user_id (AUTH_MODE=none)
        # see every event — single-user instance, no cross-user leak.
        if event_type not in self.connection_subscriptions.get(conn_id, set()):
            return False
        if target_user is None:
            return True
        conn_user = self.connection_user_ids.get(conn_id)
        return conn_user is None or conn_user == target_user

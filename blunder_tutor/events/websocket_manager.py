from __future__ import annotations

import asyncio
import contextlib
import uuid

from fastapi import WebSocket

from blunder_tutor.auth import UserId
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import Event, EventType
from blunder_tutor.observability import count, gauge


def _event_target_user(event: Event) -> str | None:
    return event.data.get("user_key") if isinstance(event.data, dict) else None


class ConnectionManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_subscriptions: dict[str, set[EventType]] = {}
        self.connection_user_ids: dict[str, UserId | None] = {}
        self._broadcast_task: asyncio.Task | None = None

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
        message = event.to_dict()
        count("ws.broadcast.sent", tags={"event_type": event.type.value})
        target_user = _event_target_user(event)
        disconnected: list[str] = []
        for conn_id, ws in list(self.active_connections.items()):
            if not self._should_deliver(conn_id, event.type, target_user):
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(conn_id)
        for conn_id in disconnected:
            await self.disconnect(conn_id, reason="send_failed")

    async def start_broadcasting(self) -> None:
        queue = await self.event_bus.subscribe(event_type=None)
        while True:
            event = await queue.get()
            await self.broadcast_event(event)

    def _should_deliver(
        self, conn_id: str, event_type: EventType, target_user: str | None
    ) -> bool:
        # When an event carries a user_key, deliver only to connections
        # authenticated as that user. Events without one (job/cache today)
        # broadcast to all subscribers; per-user plumbing for those is
        # TREK-130. Connections without a user_id (AUTH_MODE=none) see
        # every event — single-user instance, no cross-user leak possible.
        if event_type not in self.connection_subscriptions.get(conn_id, set()):
            return False
        if target_user is None:
            return True
        conn_user = self.connection_user_ids.get(conn_id)
        return conn_user is None or conn_user == target_user

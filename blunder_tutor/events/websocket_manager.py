from __future__ import annotations

import asyncio
import contextlib
import uuid

from fastapi import WebSocket

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import Event, EventType


class ConnectionManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_subscriptions: dict[str, set[EventType]] = {}
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_subscriptions[connection_id] = set()
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        self.active_connections.pop(connection_id, None)
        self.connection_subscriptions.pop(connection_id, None)

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

        # Find connections subscribed to this event type
        disconnected = []
        for conn_id, ws in list(self.active_connections.items()):
            subscriptions = self.connection_subscriptions.get(conn_id, set())

            # Send if subscribed to this specific event type
            if event.type in subscriptions:
                try:
                    await ws.send_json(message)
                except Exception:
                    # Connection dead, mark for cleanup
                    disconnected.append(conn_id)

        # Clean up dead connections
        for conn_id in disconnected:
            await self.disconnect(conn_id)

    async def start_broadcasting(self) -> None:
        queue = await self.event_bus.subscribe(event_type=None)

        while True:
            event = await queue.get()
            await self.broadcast_event(event)

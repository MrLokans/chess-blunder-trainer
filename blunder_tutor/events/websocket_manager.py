from __future__ import annotations

import asyncio
import uuid

from fastapi import WebSocket

from .event_bus import EventBus
from .event_types import Event, EventType


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
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_subscriptions:
            del self.connection_subscriptions[connection_id]

    async def subscribe(self, connection_id: str, event_types: list[str]) -> None:
        if connection_id in self.connection_subscriptions:
            # Convert strings to EventType enums
            for event_type_str in event_types:
                try:
                    event_type = EventType(event_type_str)
                    self.connection_subscriptions[connection_id].add(event_type)
                except ValueError:
                    # Invalid event type, skip
                    pass

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

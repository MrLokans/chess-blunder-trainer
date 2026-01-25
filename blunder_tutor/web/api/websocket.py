from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from blunder_tutor.events.websocket_manager import ConnectionManager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_manager: ConnectionManager = websocket.app.state.connection_manager
    connection_id = await connection_manager.connect(websocket)

    try:
        while True:
            # Receive messages from client
            message = await websocket.receive_json()

            action = message.get("action")

            if action == "subscribe":
                event_types = message.get("events", [])
                await connection_manager.subscribe(connection_id, event_types)
                await websocket.send_json({"type": "subscribed", "events": event_types})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await connection_manager.disconnect(connection_id)

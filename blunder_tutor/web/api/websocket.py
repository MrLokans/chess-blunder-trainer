import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from blunder_tutor.auth import UserId
from blunder_tutor.auth.fastapi import SESSION_COOKIE_NAME
from blunder_tutor.events.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)
router = APIRouter()

_REJECT_CODE = 4401
_REJECT_REASON = "unauthorized"


async def _resolve_user_id(websocket: WebSocket) -> tuple[bool, UserId | None]:
    """Resolve the connecting user. Returns ``(allow, user_id)``.

    ``allow=False`` means the connection must be closed with
    :data:`_REJECT_CODE`. Under ``AUTH_MODE=none`` there is no auth core,
    so every connection passes through with ``user_id=None`` (single-
    user instance — cross-user leak is structurally impossible).
    """
    auth = websocket.app.state.auth
    if auth is None:
        return True, None
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return False, None
    client_ip = websocket.client.host if websocket.client else None
    ctx = await auth.service.resolve_session(token, client_ip)
    if ctx is None:
        return False, None
    return True, ctx.user_id


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    allow, user_id = await _resolve_user_id(websocket)
    if not allow:
        await websocket.close(code=_REJECT_CODE, reason=_REJECT_REASON)
        return

    connection_manager: ConnectionManager = websocket.app.state.connection_manager
    connection_id = await connection_manager.connect(websocket, user_id=user_id)

    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "subscribe":
                event_types = message.get("events", [])
                await connection_manager.subscribe(connection_id, event_types)
                await websocket.send_json({"type": "subscribed", "events": event_types})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, reason="client_close")
    except Exception:
        logger.exception("WebSocket error")
        await connection_manager.disconnect(connection_id, reason="error")

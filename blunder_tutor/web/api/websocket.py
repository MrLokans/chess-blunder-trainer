import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from blunder_tutor.auth import UserId
from blunder_tutor.auth.fastapi import SESSION_COOKIE_NAME
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.web.middleware import _origin_matches_host

logger = logging.getLogger(__name__)
router = APIRouter()

_REJECT_CODE = 4401
_REJECT_REASON = "unauthorized"
_FORBIDDEN_ORIGIN_CODE = 4403


async def _resolve_user_id(websocket: WebSocket) -> tuple[bool, UserId | None]:
    """Returns `(allow, user_id)`; `allow=False` closes with `_REJECT_CODE`.

    Under none mode there is no auth core and every connection passes with
    `user_id=None` (single user, no cross-user leak)."""
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
    # CSRF middleware never sees WebSocket upgrades, and browsers let any page open one.
    if not _origin_matches_host(websocket):
        await websocket.close(code=_FORBIDDEN_ORIGIN_CODE, reason="forbidden origin")
        return
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
                accepted = await connection_manager.subscribe(
                    connection_id, event_types
                )
                await websocket.send_json({"type": "subscribed", "events": accepted})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, reason="client_close")
    except Exception:
        logger.exception("WebSocket error")
        await connection_manager.disconnect(connection_id, reason="error")

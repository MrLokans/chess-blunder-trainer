from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import UserContext, UserId, Username
from blunder_tutor.web.paths import AUTH_API_PREFIX, AUTH_UI_PATHS

EXEMPT_PATHS = AUTH_UI_PATHS | frozenset({"/health", "/favicon.ico"})
EXEMPT_PREFIXES = ("/static", AUTH_API_PREFIX)

_LOCAL_USER_ID = UserId("_local")
_LOCAL_USERNAME = Username("_local")


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False
    # Browser navigations often omit Accept entirely; treat any non-/api
    # path as HTML by default so the client gets a proper /login redirect
    # instead of a JSON 401.
    return not request.url.path.startswith("/api/")


def _is_exempt(path: str) -> bool:
    if path in EXEMPT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    """Resolves the per-request :class:`UserContext` from the session
    cookie and attaches it to ``request.state.user_ctx``.

    In ``auth_mode == "none"`` every request runs as a single ``_local``
    user whose DB path is ``app.state.legacy_db_path`` — preserving the
    pre-auth single-user topology untouched.

    In ``auth_mode == "credentials"`` unauthenticated requests either
    redirect HTML navigations to ``/login?next=<path>`` or return a 401
    JSON body for API callers. Exempt paths (login/signup/setup, static,
    ``/api/auth/*``) run without a context so route handlers that need
    the context must depend on :func:`get_user_context`.
    """

    async def dispatch(self, request: Request, call_next):
        mode = getattr(request.app.state, "auth_mode", "none")
        legacy_db_path: Path = request.app.state.legacy_db_path

        if mode == "none":
            request.state.user_ctx = UserContext(
                user_id=_LOCAL_USER_ID,
                username=_LOCAL_USERNAME,
                db_path=legacy_db_path,
                session_token=None,
            )
            return await call_next(request)

        path = request.url.path
        service: AuthService = request.app.state.auth_service
        token = request.cookies.get("session_token")
        client_ip = request.client.host if request.client else None
        ctx: UserContext | None = None
        if token:
            ctx = await service.resolve_session(token, client_ip)

        if _is_exempt(path):
            request.state.user_ctx = ctx
            return await call_next(request)

        if ctx is None:
            if _wants_html(request):
                return RedirectResponse(
                    url=f"/login?next={path}", status_code=302
                )
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        request.state.user_ctx = ctx
        return await call_next(request)

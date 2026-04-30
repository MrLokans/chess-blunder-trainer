from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import UserContext


@dataclass(frozen=True)
class MiddlewareConfig:
    """Per-application config for :class:`AuthMiddleware`.

    ``cookie_name`` is the cookie key the middleware reads to extract
    the session token. ``exempt_paths`` are exact-match URLs that bypass
    the auth check (login/signup/setup pages, health probes);
    ``exempt_prefixes`` are prefix-match (static asset routes, auth API
    prefix). Consumers pass only what their URL space requires — the
    auth core has no opinions about which non-API paths should be
    public.
    """

    cookie_name: str
    exempt_paths: frozenset[str] = field(default_factory=frozenset)
    exempt_prefixes: tuple[str, ...] = ()


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


class AuthMiddleware(BaseHTTPMiddleware):
    """Resolves the per-request :class:`UserContext` from the session
    cookie and attaches it to ``request.state.user_ctx``.

    Unauthenticated requests either redirect HTML navigations to
    ``/login?next=<path>`` or return a 401 JSON body for API callers.
    Exempt paths (login/signup/setup, static, ``/api/auth/*``) run
    without a context so route handlers that need the context must
    depend on :func:`get_user_context`.

    Single-user back-compat (``AUTH_MODE=none``) is a consumer-side
    concern and lives in a separate web-layer middleware
    (:class:`blunder_tutor.web.bypass_auth.BypassAuthMiddleware`); the
    two are mutually exclusive at registration time.
    """

    def __init__(self, app, config: MiddlewareConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        auth = request.app.state.auth
        assert auth is not None  # AuthMiddleware mounted → credentials bootstrap ran
        service: AuthService = auth.service
        token = request.cookies.get(self._config.cookie_name)
        client_ip = request.client.host if request.client else None
        ctx: UserContext | None = None
        if token:
            ctx = await service.resolve_session(token, client_ip)

        if self._is_exempt(path):
            request.state.user_ctx = ctx
            return await call_next(request)

        if ctx is None:
            if _wants_html(request):
                return RedirectResponse(
                    url=f"/login?next={path}", status_code=status.HTTP_302_FOUND
                )
            return JSONResponse(
                {"error": "unauthorized"}, status_code=status.HTTP_401_UNAUTHORIZED
            )

        request.state.user_ctx = ctx
        return await call_next(request)

    def _is_exempt(self, path: str) -> bool:
        if path in self._config.exempt_paths:
            return True
        return any(path.startswith(prefix) for prefix in self._config.exempt_prefixes)

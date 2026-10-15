from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import UserContext


@dataclass(frozen=True)
class MiddlewareConfig:
    cookie_name: str
    exempt_paths: frozenset[str] = field(default_factory=frozenset)
    exempt_prefixes: tuple[str, ...] = ()


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False
    # Browsers often omit Accept; treat non-/api paths as HTML so users get a /login
    # redirect, not a JSON 401.
    return not request.url.path.startswith("/api/")


class AuthMiddleware(BaseHTTPMiddleware):
    """Exempt paths run without a user context. Mutually exclusive with
    `BypassAuthMiddleware`."""

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

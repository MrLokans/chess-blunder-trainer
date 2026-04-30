"""FastAPI integration surface — the one allowed sub-namespace.

Consumers import directly from ``blunder_tutor.auth.fastapi`` (rather
than the top-level ``blunder_tutor.auth``) when they need pieces that
only make sense in a FastAPI app: middleware, request-scoped
dependencies, cookie helpers, the auth router factory and its
extension Protocols. Everything else (entities, errors, service,
providers, storage) goes through the top-level package so the auth
core stays usable without FastAPI on the import path.
"""

from blunder_tutor.auth.fastapi.cookies import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from blunder_tutor.auth.fastapi.dependencies import UserContextDep, get_user_context
from blunder_tutor.auth.fastapi.errors import DefaultErrorCodec
from blunder_tutor.auth.fastapi.middleware import AuthMiddleware, MiddlewareConfig
from blunder_tutor.auth.fastapi.protocols import RateLimiter
from blunder_tutor.auth.fastapi.router import (
    CookieAdapter,
    LoginRequest,
    MeResponse,
    SignupRequest,
    build_auth_router,
)

__all__ = [
    "SESSION_COOKIE_NAME",
    "AuthMiddleware",
    "CookieAdapter",
    "DefaultErrorCodec",
    "LoginRequest",
    "MeResponse",
    "MiddlewareConfig",
    "RateLimiter",
    "SignupRequest",
    "UserContextDep",
    "build_auth_router",
    "clear_session_cookie",
    "get_user_context",
    "set_session_cookie",
]

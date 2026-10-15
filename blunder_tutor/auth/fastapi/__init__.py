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

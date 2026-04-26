"""FastAPI integration surface — the one allowed sub-namespace.

Consumers import directly from ``blunder_tutor.auth.fastapi`` (rather
than the top-level ``blunder_tutor.auth``) when they need pieces that
only make sense in a FastAPI app: middleware, request-scoped
dependencies, cookie helpers. Everything else (entities, errors,
service, providers, storage) goes through the top-level package so
the auth core stays usable without FastAPI on the import path.
"""

from blunder_tutor.auth.fastapi.cookies import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from blunder_tutor.auth.fastapi.dependencies import UserContextDep, get_user_context
from blunder_tutor.auth.fastapi.middleware import AuthMiddleware, MiddlewareConfig

__all__ = [
    "SESSION_COOKIE_NAME",
    "AuthMiddleware",
    "MiddlewareConfig",
    "UserContextDep",
    "clear_session_cookie",
    "get_user_context",
    "set_session_cookie",
]

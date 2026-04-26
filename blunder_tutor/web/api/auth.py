"""blunder_tutor's auth API surface — a thin wrapper around
:func:`blunder_tutor.auth.fastapi.build_auth_router`.

Wires the library factory with project-specific defaults: the
session-cookie setter that knows about ``AppConfig`` (TLS,
trusted-proxy, ``AUTH_COOKIE_SECURE`` override), the per-IP rate
limiters from ``app.state``, and the auth-service lookup from the
``AuthResources`` bundle. Cache invalidation on account delete is
composed into the ``on_after_delete`` hook on :class:`AuthService` at
construction time (see ``web/auth_hooks.py``); the route itself is
just a thin pass-through.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, Response
from fastapi_throttle import RateLimiter

from blunder_tutor.auth import AuthService
from blunder_tutor.auth.fastapi import build_auth_router
from blunder_tutor.web.cookies import (
    clear_session_cookie,
)
from blunder_tutor.web.cookies import (
    set_session_cookie as _set_session_cookie,
)


def _auth_service_provider(request: Request) -> AuthService:
    auth = request.app.state.auth
    if auth is None:
        # Credentials mode not active — auth endpoints are offline.
        raise HTTPException(status_code=404)
    return auth.service


def _set_session_cookie_with_config(
    response: Response, token: str, request: Request
) -> None:
    # ``web.cookies.set_session_cookie`` takes ``AppConfig`` for the
    # Secure flag computation; the router factory's contract is
    # ``(response, token, request)`` so we pull the config off
    # ``app.state`` here, keeping AppConfig out of the auth library.
    _set_session_cookie(response, token, request.app.state.config, request)


async def _login_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.login_rate_limiter
    await limiter(request, response)


async def _signup_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.signup_rate_limiter
    await limiter(request, response)


router = build_auth_router(
    auth_service_provider=_auth_service_provider,
    set_session_cookie=_set_session_cookie_with_config,
    clear_session_cookie=clear_session_cookie,
    login_dependencies=[_login_rate_limit],
    signup_dependencies=[_signup_rate_limit],
)

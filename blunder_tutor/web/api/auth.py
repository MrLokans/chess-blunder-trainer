from __future__ import annotations

from fastapi import HTTPException, Request, Response, status
from fastapi_throttle import RateLimiter

from blunder_tutor.auth import AuthService
from blunder_tutor.auth.fastapi import (
    CookieAdapter,
    build_auth_router,
    clear_session_cookie,
)
from blunder_tutor.web.cookies import set_session_cookie as _set_session_cookie


def _auth_service_provider(request: Request) -> AuthService:
    auth = request.app.state.auth
    if auth is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return auth.service


def _set_session_cookie_with_config(
    response: Response, token: str, request: Request
) -> None:
    # `web.cookies.set_session_cookie` needs AppConfig for `Secure`; the factory
    # contract is `(response, token, request)`, so the config is pulled from `app.state`
    # here to keep AppConfig out of the library.
    _set_session_cookie(response, token, request.app.state.config, request)


async def _login_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.login_rate_limiter
    await limiter(request, response)


async def _signup_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.signup_rate_limiter
    await limiter(request, response)


router = build_auth_router(
    auth_service_provider=_auth_service_provider,
    cookies=CookieAdapter(
        set_cookie=_set_session_cookie_with_config,
        clear_cookie=clear_session_cookie,
    ),
    login_dependencies=[_login_rate_limit],
    signup_dependencies=[_signup_rate_limit],
)

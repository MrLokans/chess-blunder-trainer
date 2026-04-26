"""blunder_tutor-flavoured wrapper around the generic session-cookie
helpers in :mod:`blunder_tutor.auth.fastapi.cookies`.

The auth-library half (cookie name, set/clear primitives) lives in
the auth package; this module hosts the AppConfig-aware ``Secure``
flag computation so the auth core doesn't have to know about
:class:`AppConfig` or trusted-proxy semantics.
"""

from __future__ import annotations

from fastapi import Request, Response

from blunder_tutor.auth.fastapi import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
)
from blunder_tutor.auth.fastapi import (
    set_session_cookie as _set_session_cookie,
)
from blunder_tutor.web.config import AppConfig
from blunder_tutor.web.tls import is_https_request

__all__ = [
    "SESSION_COOKIE_NAME",
    "clear_session_cookie",
    "compute_cookie_secure",
    "set_session_cookie",
]


def compute_cookie_secure(config: AppConfig, request: Request) -> bool:
    """Session cookie ``Secure`` flag.

    Precedence:
    1. Explicit ``AUTH_COOKIE_SECURE`` override (highest priority —
       operators can force-on behind any topology).
    2. Request arrived over TLS (direct or via trusted proxy).
    3. Fallback ``False`` — a direct-to-uvicorn plain-HTTP deploy.
       Documented as an operator misconfiguration for any public-facing
       instance (boot-time warning emitted when both knobs are unset in
       credentials mode).
    """
    if config.auth.cookie_secure is not None:
        return config.auth.cookie_secure
    return is_https_request(request, config.auth)


def set_session_cookie(
    response: Response,
    token: str,
    config: AppConfig,
    request: Request,
) -> None:
    _set_session_cookie(
        response,
        token,
        max_age=config.auth.session_max_age_seconds,
        secure=compute_cookie_secure(config, request),
    )

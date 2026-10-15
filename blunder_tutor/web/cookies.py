from __future__ import annotations

from fastapi import Request, Response

from blunder_tutor.auth.fastapi import set_session_cookie as _set_session_cookie
from blunder_tutor.web.config import AppConfig
from blunder_tutor.web.tls import is_https_request


def compute_cookie_secure(config: AppConfig, request: Request) -> bool:
    """Precedence: explicit `AUTH_COOKIE_SECURE`, then request arrived over TLS (direct or
    trusted proxy), else False (plain-HTTP deploy; warned at boot in credentials mode).
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

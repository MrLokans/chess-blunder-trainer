from __future__ import annotations

from fastapi import Request, Response

from blunder_tutor.web.config import AppConfig
from blunder_tutor.web.tls import is_https_request

SESSION_COOKIE_NAME = "session_token"
_SESSION_COOKIE_PATH = "/"
_SESSION_COOKIE_SAMESITE = "lax"


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
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=config.auth.session_max_age_seconds,
        httponly=True,
        samesite=_SESSION_COOKIE_SAMESITE,
        secure=compute_cookie_secure(config, request),
        path=_SESSION_COOKIE_PATH,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path=_SESSION_COOKIE_PATH)

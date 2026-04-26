"""Session cookie helpers — pure web-layer plumbing without consumer-
specific config types.

Callers compute the ``Secure`` / ``SameSite`` / ``max_age`` values from
their own configuration and pass them in. Anything that depends on
blunder_tutor's :class:`AppConfig` (HTTPS detection, trusted-proxy
handling) lives in ``blunder_tutor/web/cookies.py`` and wraps these
primitives.
"""

from __future__ import annotations

from typing import Literal

from fastapi import Response

SESSION_COOKIE_NAME = "session_token"
_SESSION_COOKIE_PATH = "/"

SameSite = Literal["lax", "strict", "none"]


def set_session_cookie(
    response: Response,
    token: str,
    *,
    max_age: int,
    secure: bool,
    samesite: SameSite = "lax",
) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path=_SESSION_COOKIE_PATH,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path=_SESSION_COOKIE_PATH)

"""Single-user bypass middleware for ``AUTH_MODE=none``.

Lives in the web layer, not the auth core: the ``_local`` user is a
blunder_tutor back-compat concern (existing single-user installs that
predate the credentials-mode topology). A library consumer would
either skip auth entirely or run the credentials-mode middleware —
neither needs this synthetic-user shape.

Mutually exclusive with :class:`blunder_tutor.auth.middleware.AuthMiddleware`:
``app.py`` registers exactly one of the two based on ``config.auth.mode``.
"""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.auth.types import UserContext, UserId, Username

# Synthetic identifiers for the AUTH_MODE=none single user. The literal
# values are also referenced as a cache-key fallback in
# ``web/request_helpers.py`` and as a saved-locale key in ``app.py`` —
# any rename here must update those consumers in lockstep, which
# ``tests/test_bypass_auth.py::test_local_constants_match_legacy_sentinel``
# pins.
LOCAL_USER_ID = UserId("_local")
LOCAL_USERNAME = Username("_local")


class BypassAuthMiddleware(BaseHTTPMiddleware):
    """Attach a fixed ``_local`` :class:`UserContext` to every request.

    Skips session resolution entirely — any ``session_token`` cookie on
    the request is ignored. Downstream middleware (``UserDbPathMiddleware``,
    ``SetupCheckMiddleware``, ``LocaleMiddleware``) sees a non-``None``
    ``user_ctx`` and behaves identically to the credentials-mode
    authenticated path, with the per-user DB resolver returning the
    legacy single-user database.
    """

    async def dispatch(self, request: Request, call_next):
        request.state.user_ctx = UserContext(
            user_id=LOCAL_USER_ID,
            username=LOCAL_USERNAME,
            session_token=None,
        )
        return await call_next(request)

"""Lives in the web layer because the synthetic `_local` user is a blunder_tutor
back-compat concern. Mutually exclusive with `AuthMiddleware`."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.auth import UserContext, UserId, Username

# Also the cache-key fallback in `request_helpers.py` and the saved-locale key in
# `app.py`; `tests/test_bypass_auth.py` pins them in lockstep.
LOCAL_USER_ID = UserId("_local")
LOCAL_USERNAME = Username("_local")


class BypassAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user_ctx = UserContext(
            user_id=LOCAL_USER_ID,
            username=LOCAL_USERNAME,
            session_token=None,
        )
        return await call_next(request)

from __future__ import annotations

import types

from fastapi import Request

from blunder_tutor.auth import UserContext, UserId, Username
from blunder_tutor.cache.backend import CacheBackend
from blunder_tutor.web.dependencies import set_request_scope


def make_user_ctx(user_id: str, username: str | None = None) -> UserContext:
    return UserContext(
        user_id=UserId(user_id),
        username=Username(username or user_id),
        session_token=None,
    )


async def scoped_request(
    ctx: UserContext,
    backend: CacheBackend,
    *,
    default_ttl: int = 300,
    method: str = "GET",
    path: str = "/x",
) -> Request:
    """A Request whose `user_scope` was resolved by the production
    `set_request_scope` dependency from `ctx` — cache tests must exercise
    the real write-path scope derivation, never a hard-coded literal that
    could mask a write-vs-invalidate key mismatch.
    """
    app = types.SimpleNamespace(
        state=types.SimpleNamespace(
            cache=backend,
            config=types.SimpleNamespace(
                cache=types.SimpleNamespace(default_ttl=default_ttl)
            ),
        )
    )
    request = Request(
        {"type": "http", "method": method, "path": path, "headers": [], "app": app}
    )
    request.state.user_ctx = ctx
    await set_request_scope(request)
    return request

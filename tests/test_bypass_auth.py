"""Tests for the AUTH_MODE=none bypass middleware.

These tests cover behaviour that previously lived in
``tests/auth/test_middleware.py`` under the ``TestModeNone`` class
back when AUTH_MODE=none was a branch inside ``AuthMiddleware``. After
TREK-54 the bypass is a separate web-layer middleware so the auth
core no longer carries any awareness of single-user mode.
"""

from __future__ import annotations

from http import HTTPStatus
import httpx
from fastapi import FastAPI, Request
from httpx import ASGITransport

from blunder_tutor.web.bypass_auth import (
    LOCAL_USER_ID,
    LOCAL_USERNAME,
    BypassAuthMiddleware,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(BypassAuthMiddleware)

    @app.get("/echo")
    async def echo(request: Request):
        ctx = getattr(request.state, "user_ctx", None)
        return {
            "user_id": ctx.user_id if ctx else None,
            "username": ctx.username if ctx else None,
            "session_token": ctx.session_token if ctx else None,
            "is_authenticated": ctx.is_authenticated if ctx else None,
        }

    @app.get("/api/echo")
    async def api_echo(request: Request):
        ctx = getattr(request.state, "user_ctx", None)
        return {"user_id": ctx.user_id if ctx else None}

    return app


def _client(
    app: FastAPI, *, cookies: dict[str, str] | None = None
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    )


class TestBypassAuthMiddleware:
    async def test_sets_local_user_context(self):
        app = _make_app()
        async with _client(app) as client:
            r = await client.get("/echo")
        assert r.status_code == HTTPStatus.OK
        body = r.json()
        assert body["user_id"] == LOCAL_USER_ID
        assert body["username"] == LOCAL_USERNAME
        assert body["session_token"] is None
        # Bypassed contexts are not authenticated — every reader checks
        # this property to decide whether session-bound machinery (cookie
        # rotation, audit logging) should fire.
        assert body["is_authenticated"] is False

    async def test_local_constants_match_legacy_sentinel(self):
        # The literal `"_local"` is referenced as a cache key fallback in
        # `web/request_helpers.py` and as a saved-locale key in app.py.
        # Pin the values so a rename anywhere requires updating the
        # consumers in lockstep.
        assert LOCAL_USER_ID == "_local"
        assert LOCAL_USERNAME == "_local"

    async def test_api_path_is_not_blocked(self):
        # AuthMiddleware in credentials mode would 401 here. Bypass mode
        # treats /api the same as everything else: there is one user, no
        # session resolution, no exemption logic.
        app = _make_app()
        async with _client(app) as client:
            r = await client.get("/api/echo")
        assert r.status_code == HTTPStatus.OK
        assert r.json()["user_id"] == LOCAL_USER_ID

    async def test_session_cookie_is_ignored(self):
        # Stale cookies must never alter the synthetic context — otherwise
        # a leftover credentials-mode cookie could leak across a mode
        # downgrade and surface someone else's user_id in the bypass.
        app = _make_app()
        async with _client(app, cookies={"session_token": "anything"}) as client:
            r = await client.get("/echo")
        assert r.status_code == HTTPStatus.OK
        assert r.json()["user_id"] == LOCAL_USER_ID

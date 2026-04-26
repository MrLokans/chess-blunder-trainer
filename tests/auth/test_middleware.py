from __future__ import annotations

from datetime import timedelta
from functools import partial
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from blunder_tutor.auth import (
    AuthDb,
    AuthMiddleware,
    AuthService,
    MiddlewareConfig,
    SqliteStorage,
    Username,
)
from blunder_tutor.web.auth_hooks import resolve_user_db_path
from blunder_tutor.web.middleware import UserDbPathMiddleware
from blunder_tutor.web.resources import AuthResources
from tests.helpers.auth import build_test_auth_service

# Test config mirrors prod's exempt set so the middleware behaviour
# matches what production users see end-to-end. Hardcoded here (not
# imported from blunder_tutor.web.paths) so a refactor of those URL
# constants doesn't silently shift test behaviour.
_TEST_MIDDLEWARE_CONFIG = MiddlewareConfig(
    cookie_name="session_token",
    exempt_paths=frozenset(
        {"/login", "/signup", "/setup", "/logout", "/health", "/favicon.ico"}
    ),
    exempt_prefixes=("/static", "/api/auth/"),
)


def _make_app(
    service: AuthService,
    *,
    auth_db: AuthDb,
    users_dir: Path,
) -> FastAPI:
    app = FastAPI()
    app.state.auth = AuthResources(
        storage=SqliteStorage(auth_db),
        service=service,
        db_path=auth_db.path,
        users_dir=users_dir,
    )
    app.state.db_path_resolver = partial(resolve_user_db_path, users_dir)
    app.add_middleware(UserDbPathMiddleware)
    app.add_middleware(AuthMiddleware, config=_TEST_MIDDLEWARE_CONFIG)

    @app.get("/echo")
    async def echo(request: Request):
        ctx = getattr(request.state, "user_ctx", None)
        return {
            "user_id": ctx.user_id if ctx else None,
            "username": ctx.username if ctx else None,
            "db_path": str(getattr(request.state, "user_db_path", None)),
        }

    @app.get("/api/echo")
    async def api_echo(request: Request):
        ctx = getattr(request.state, "user_ctx", None)
        return {"user_id": ctx.user_id if ctx else None}

    @app.get("/login")
    async def login(request: Request):
        return {"ok": True}

    return app


def _client(
    app: FastAPI,
    *,
    follow_redirects: bool = True,
    cookies: dict[str, str] | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=follow_redirects,
        cookies=cookies,
    )


@pytest.fixture
def service(service_factory) -> AuthService:
    return service_factory(
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


@pytest.fixture
def wired_credentials_app(
    service: AuthService, auth_db: AuthDb, tmp_path: Path
) -> FastAPI:
    """Pre-wired credentials-mode app with `service` + the matching
    `AuthDb` and `users_dir` from the conftest fixtures, so individual
    tests don't repeat the AuthResources construction."""
    return _make_app(
        service,
        auth_db=auth_db,
        users_dir=tmp_path / "users",
    )


class TestModeCredentials:
    async def test_redirects_html_when_no_session(self, wired_credentials_app: FastAPI):
        app = wired_credentials_app
        async with _client(app, follow_redirects=False) as client:
            r = await client.get("/echo", headers={"accept": "text/html"})
        assert r.status_code == 302
        assert r.headers["location"].startswith("/login")
        assert "next=/echo" in r.headers["location"]

    async def test_returns_401_for_api(self, wired_credentials_app: FastAPI):
        app = wired_credentials_app
        async with _client(app) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401
        assert r.json()["error"] == "unauthorized"

    async def test_valid_session_sets_context(
        self, service: AuthService, wired_credentials_app: FastAPI
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = wired_credentials_app
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == user.id

    async def test_valid_session_sets_user_dir_as_db_path(
        self, service: AuthService, wired_credentials_app: FastAPI, tmp_path: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = wired_credentials_app
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/echo")
        assert r.status_code == 200
        assert r.json()["db_path"] == str(
            resolve_user_db_path(tmp_path / "users", user.id)
        )

    async def test_invalid_session_cookie_returns_401_for_api(
        self, wired_credentials_app: FastAPI
    ):
        app = wired_credentials_app
        async with _client(
            app, cookies={"session_token": "not-a-real-token"}
        ) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401

    async def test_exempt_paths_pass_without_session(
        self, wired_credentials_app: FastAPI
    ):
        app = wired_credentials_app
        async with _client(app) as client:
            r = await client.get("/login")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_api_auth_prefix_is_exempt(self, wired_credentials_app: FastAPI):
        app = wired_credentials_app

        @app.get("/api/auth/status")
        async def auth_status(request: Request):
            return {"ok": True}

        async with _client(app) as client:
            r = await client.get("/api/auth/status")
        assert r.status_code == 200

    async def test_exempt_path_with_valid_session_still_sets_ctx(
        self, service: AuthService, wired_credentials_app: FastAPI
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = wired_credentials_app

        @app.get("/login/echo")
        async def login_echo(request: Request):
            ctx = getattr(request.state, "user_ctx", None)
            return {"user_id": ctx.user_id if ctx else None}

        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/login/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == user.id

    async def test_expired_session_returns_401_for_api(
        self, service: AuthService, auth_db: AuthDb, tmp_path: Path
    ):
        users_dir = tmp_path / "users"
        short_lived = build_test_auth_service(
            auth_db=auth_db,
            users_dir=users_dir,
            session_max_age=timedelta(seconds=-1),
            session_idle=timedelta(days=1),
        )
        user = await short_lived.register(
            username=Username("alice"), password="password123"
        )
        session = await short_lived.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = _make_app(
            short_lived,
            auth_db=auth_db,
            users_dir=tmp_path / "users",
        )
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from blunder_tutor.auth.middleware import AuthMiddleware
from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import Username


def _make_app(
    service: AuthService | None,
    *,
    mode: str,
    legacy_db_path: Path,
) -> FastAPI:
    app = FastAPI()
    app.state.auth_service = service
    app.state.auth_mode = mode
    app.state.legacy_db_path = legacy_db_path
    app.add_middleware(AuthMiddleware)

    @app.get("/echo")
    async def echo(request: Request):
        ctx = getattr(request.state, "user_ctx", None)
        return {
            "user_id": ctx.user_id if ctx else None,
            "username": ctx.username if ctx else None,
            "db_path": str(ctx.db_path) if ctx else None,
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
def legacy_db(tmp_path: Path) -> Path:
    p = tmp_path / "main.sqlite3"
    p.touch()
    return p


@pytest.fixture
def service(service_factory) -> AuthService:
    return service_factory(
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


class TestModeNone:
    async def test_sets_local_sentinel(self, legacy_db: Path):
        app = _make_app(None, mode="none", legacy_db_path=legacy_db)
        async with _client(app) as client:
            r = await client.get("/echo")
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == "_local"
        assert data["username"] == "_local"
        assert data["db_path"] == str(legacy_db)

    async def test_mode_none_bypasses_exempt_check(self, legacy_db: Path):
        app = _make_app(None, mode="none", legacy_db_path=legacy_db)
        async with _client(app) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == "_local"


class TestModeCredentials:
    async def test_redirects_html_when_no_session(
        self, service: AuthService, legacy_db: Path
    ):
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app, follow_redirects=False) as client:
            r = await client.get("/echo", headers={"accept": "text/html"})
        assert r.status_code == 302
        assert r.headers["location"].startswith("/login")
        assert "next=/echo" in r.headers["location"]

    async def test_returns_401_for_api(self, service: AuthService, legacy_db: Path):
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401
        assert r.json()["error"] == "unauthorized"

    async def test_valid_session_sets_context(
        self, service: AuthService, legacy_db: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == user.id

    async def test_valid_session_sets_user_dir_as_db_path(
        self, service: AuthService, legacy_db: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/echo")
        assert r.status_code == 200
        assert r.json()["db_path"] == str(service.db_path_for(user.id))

    async def test_invalid_session_cookie_returns_401_for_api(
        self, service: AuthService, legacy_db: Path
    ):
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(
            app, cookies={"session_token": "not-a-real-token"}
        ) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401

    async def test_exempt_paths_pass_without_session(
        self, service: AuthService, legacy_db: Path
    ):
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app) as client:
            r = await client.get("/login")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_api_auth_prefix_is_exempt(
        self, service: AuthService, legacy_db: Path
    ):
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)

        @app.get("/api/auth/status")
        async def auth_status(request: Request):
            return {"ok": True}

        async with _client(app) as client:
            r = await client.get("/api/auth/status")
        assert r.status_code == 200

    async def test_exempt_path_with_valid_session_still_sets_ctx(
        self, service: AuthService, legacy_db: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = _make_app(service, mode="credentials", legacy_db_path=legacy_db)

        @app.get("/login/echo")
        async def login_echo(request: Request):
            ctx = getattr(request.state, "user_ctx", None)
            return {"user_id": ctx.user_id if ctx else None}

        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/login/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == user.id

    async def test_expired_session_returns_401_for_api(
        self, service: AuthService, legacy_db: Path
    ):
        short_lived = AuthService(
            auth_db=service._db,
            users_dir=service._users_dir,
            session_max_age=timedelta(seconds=-1),
            session_idle=timedelta(days=1),
        )
        user = await short_lived.register(
            username=Username("alice"), password="password123"
        )
        session = await short_lived.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        app = _make_app(short_lived, mode="credentials", legacy_db_path=legacy_db)
        async with _client(app, cookies={"session_token": session.token}) as client:
            r = await client.get("/api/echo")
        assert r.status_code == 401


class TestModeNoneIgnoresSessionCookie:
    async def test_cookie_does_not_override_local_sentinel(self, legacy_db: Path):
        app = _make_app(None, mode="none", legacy_db_path=legacy_db)
        async with _client(app, cookies={"session_token": "anything"}) as client:
            r = await client.get("/echo")
        assert r.status_code == 200
        assert r.json()["user_id"] == "_local"

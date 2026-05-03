from __future__ import annotations

from datetime import timedelta
from functools import partial
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from blunder_tutor.auth import (
    AuthDb,
    AuthMiddleware,
    MiddlewareConfig,
    SqliteStorage,
    UserContext,
    UserId,
    Username,
)
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web.auth_hooks import resolve_user_db_path
from blunder_tutor.web.middleware import (
    LocaleMiddleware,
    SetupCheckMiddleware,
    UserDbPathMiddleware,
)
from blunder_tutor.web.per_user_cache import PerUserCache
from blunder_tutor.web.request_helpers import _cache_key, _db_path_for
from blunder_tutor.web.resources import AuthResources
from tests.helpers.auth import build_test_auth_service


def _client(app: FastAPI, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
        cookies={"session_token": token},
    )


class TestCacheKey:
    def test_returns_user_id_when_context_set(self):
        request = SimpleNamespace(
            state=SimpleNamespace(
                user_ctx=UserContext(
                    user_id=UserId("abc123"),
                    username=Username("alice"),
                    session_token=None,
                )
            )
        )
        assert _cache_key(request) == "abc123"

    def test_returns_local_sentinel_when_no_context(self):
        request = SimpleNamespace(state=SimpleNamespace())
        assert _cache_key(request) == "_local"


class TestDbPathFor:
    def test_returns_user_db_path_when_set(self, tmp_path: Path):
        db = tmp_path / "user.sqlite3"
        request = SimpleNamespace(state=SimpleNamespace(user_db_path=db))
        assert _db_path_for(request) == db

    def test_returns_none_when_user_db_path_unset(self):
        request = SimpleNamespace(state=SimpleNamespace())
        assert _db_path_for(request) is None


@pytest.fixture
async def two_user_app(auth_db: AuthDb, tmp_path: Path):
    """Build a minimal app with AuthMiddleware + SetupCheckMiddleware +
    LocaleMiddleware + two registered users (A completes setup, B does
    not). Returns (app, user_a, token_a, user_b, token_b, service).
    """
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    service = build_test_auth_service(
        auth_db=auth_db,
        users_dir=users_dir,
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )

    user_a = await service.register(username=Username("alice"), password="password123")
    user_b = await service.register(username=Username("bob"), password="password123")

    # Alice completes setup in her own DB; Bob leaves his DB in default
    # (not-setup) state. run_migrations already ran during register() so
    # both per-user DBs exist; we only need to flip Alice's
    # setup_completed flag via SettingsRepository.
    repo = SettingsRepository(db_path=resolve_user_db_path(users_dir, user_a.id))
    try:
        await repo.mark_setup_completed()
    finally:
        await repo.close()

    session_a = await service.create_session(
        user_id=user_a.id, user_agent=None, ip=None
    )
    session_b = await service.create_session(
        user_id=user_b.id, user_agent=None, ip=None
    )

    app = FastAPI()
    app.state.auth = AuthResources(
        storage=SqliteStorage(auth_db),
        service=service,
        db_path=auth_db.path,
        users_dir=users_dir,
    )
    app.state.auth_mode = "credentials"
    app.state.demo_mode = False
    app.state.db_path_resolver = partial(resolve_user_db_path, users_dir)
    # SetupCheckMiddleware + LocaleMiddleware expect these:
    app.state.i18n = None
    app.state.templates = SimpleNamespace(env=SimpleNamespace(globals={}))
    app.state.setup_completed_cache = PerUserCache[bool]()
    app.state.locale_cache = PerUserCache[str]()
    app.state.features_cache = PerUserCache[dict[str, bool]]()

    @app.get("/some-page")
    async def some_page(request: Request):
        return {"user_id": request.state.user_ctx.user_id}

    # Order: last added = first executed. AuthMiddleware must run first
    # so the next-added UserDbPathMiddleware can read its `user_ctx`.
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(LocaleMiddleware)
    app.add_middleware(UserDbPathMiddleware)
    app.add_middleware(
        AuthMiddleware,
        config=MiddlewareConfig(cookie_name="session_token"),
    )

    return app, user_a, session_a.token, user_b, session_b.token, service


class TestSetupCacheIsolation:
    """Regression for the Phase 3 review Critical-1 finding: a global
    `_setup_completed_cache` leaked user A's "setup done" state to user
    B, letting B skip `/setup` even though their per-user DB had not been
    initialized."""

    async def test_user_b_still_redirected_to_setup_after_user_a_completes(
        self, two_user_app
    ):
        app, _user_a, token_a, _user_b, token_b, _ = two_user_app

        # Two clients (one per user) rather than one client with per-request
        # cookies — httpx deprecates the latter, and two clients model the
        # "two browsers, two sessions" reality the test is asserting against.
        async with _client(app, token_a) as client_a:
            r_a = await client_a.get("/some-page")
            assert r_a.status_code == HTTPStatus.OK

        async with _client(app, token_b) as client_b:
            r_b = await client_b.get("/some-page")
        assert r_b.status_code == HTTPStatus.SEE_OTHER
        assert r_b.headers["location"] == "/setup"

    async def test_cache_stores_per_user_keys(self, two_user_app):
        app, user_a, token_a, user_b, token_b, _ = two_user_app

        async with _client(app, token_a) as client_a:
            await client_a.get("/some-page")

        async with _client(app, token_b) as client_b:
            await client_b.get("/some-page")

        cache = app.state.setup_completed_cache
        assert cache.get(user_a.id) is True
        assert cache.get(user_b.id) is False


class TestLocaleCacheIsolation:
    def test_per_user_cache_keeps_users_separate(self):
        cache: PerUserCache[str] = PerUserCache()
        cache.set("user_a", "ru")
        cache.set("user_b", "es")
        assert cache.get("user_a") == "ru"
        assert cache.get("user_b") == "es"
        assert cache.get("user_c") is None

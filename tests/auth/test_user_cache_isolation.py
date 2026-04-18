from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.middleware import AuthMiddleware
from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import UserContext, UserId, Username
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web.middleware import (
    LocaleMiddleware,
    SetupCheckMiddleware,
    _cache_key,
    _db_path_for,
    set_locale_cache,
)


class TestCacheKey:
    def test_returns_user_id_when_context_set(self):
        request = SimpleNamespace(
            state=SimpleNamespace(
                user_ctx=UserContext(
                    user_id=UserId("abc123"),
                    username=Username("alice"),
                    db_path=Path("/tmp/a.sqlite3"),
                    session_token=None,
                )
            )
        )
        assert _cache_key(request) == "abc123"

    def test_returns_local_sentinel_when_no_context(self):
        request = SimpleNamespace(state=SimpleNamespace())
        assert _cache_key(request) == "_local"


class TestDbPathFor:
    def test_returns_ctx_db_path_when_context_set(self, tmp_path: Path):
        db = tmp_path / "user.sqlite3"
        request = SimpleNamespace(
            state=SimpleNamespace(
                user_ctx=UserContext(
                    user_id=UserId("abc"),
                    username=Username("alice"),
                    db_path=db,
                    session_token=None,
                )
            ),
            app=SimpleNamespace(state=SimpleNamespace(auth_mode="credentials")),
        )
        assert _db_path_for(request) == db

    def test_returns_none_in_credentials_mode_without_ctx(self):
        request = SimpleNamespace(
            state=SimpleNamespace(),
            app=SimpleNamespace(state=SimpleNamespace(auth_mode="credentials")),
        )
        assert _db_path_for(request) is None

    def test_returns_legacy_path_in_none_mode_without_ctx(self, tmp_path: Path):
        legacy = tmp_path / "main.sqlite3"
        request = SimpleNamespace(
            state=SimpleNamespace(),
            app=SimpleNamespace(
                state=SimpleNamespace(
                    auth_mode="none",
                    config=SimpleNamespace(data=SimpleNamespace(db_path=legacy)),
                )
            ),
        )
        assert _db_path_for(request) == legacy


@pytest.fixture
async def two_user_app(auth_db: AuthDb, tmp_path: Path):
    """Build a minimal app with AuthMiddleware + SetupCheckMiddleware +
    LocaleMiddleware + two registered users (A completes setup, B does
    not). Returns (app, user_a_token, user_b_token, service).
    """
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    service = AuthService(
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
    repo = SettingsRepository(db_path=service.db_path_for(user_a.id))
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
    app.state.auth_service = service
    app.state.auth_mode = "credentials"
    app.state.legacy_db_path = tmp_path / "unused.sqlite3"
    app.state.demo_mode = False
    # SetupCheckMiddleware + LocaleMiddleware expect these:
    app.state.i18n = None
    app.state.templates = SimpleNamespace(env=SimpleNamespace(globals={}))

    @app.get("/some-page")
    async def some_page(request: Request):
        return {"user_id": request.state.user_ctx.user_id}

    # Order: last added = first executed. AuthMiddleware must run first.
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(LocaleMiddleware)
    app.add_middleware(AuthMiddleware)

    return app, session_a.token, session_b.token, service


class TestSetupCacheIsolation:
    """Regression for the Phase 3 review Critical-1 finding: a global
    `_setup_completed_cache` leaked user A's "setup done" state to user
    B, letting B skip `/setup` even though their per-user DB had not been
    initialized."""

    async def test_user_b_still_redirected_to_setup_after_user_a_completes(
        self, two_user_app
    ):
        app, token_a, token_b, _ = two_user_app

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            # Warm the cache with user A (setup completed, no redirect).
            r_a = await client.get("/some-page", cookies={"session_token": token_a})
            assert r_a.status_code == 200

            # User B must still be redirected to /setup; they don't share
            # user A's cache entry.
            r_b = await client.get("/some-page", cookies={"session_token": token_b})
        assert r_b.status_code == 303
        assert r_b.headers["location"] == "/setup"

    async def test_cache_stores_per_user_keys(self, two_user_app):
        app, token_a, token_b, _ = two_user_app

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            await client.get("/some-page", cookies={"session_token": token_a})
            await client.get("/some-page", cookies={"session_token": token_b})

        cache = app.state._setup_completed_cache
        assert isinstance(cache, dict)
        # Two distinct keys, one True (alice), one False (bob).
        assert len(cache) == 2
        assert True in cache.values()
        assert False in cache.values()


class TestLocaleCacheIsolation:
    def test_set_locale_cache_keeps_users_separate(self):
        app_state = SimpleNamespace()
        request = SimpleNamespace(app=SimpleNamespace(state=app_state))

        set_locale_cache(request, "user_a", "ru")
        set_locale_cache(request, "user_b", "es")

        assert app_state._locale_cache == {"user_a": "ru", "user_b": "es"}

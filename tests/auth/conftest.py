from __future__ import annotations

import argparse
import contextlib
import os
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from blunder_tutor.auth import (
    AuthDb,
    AuthService,
    BcryptHasher,
    ValidationRules,
    initialize_auth_schema,
)
from blunder_tutor.auth import hashers as _hashers_module
from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import config_factory
from tests.helpers.auth import TEST_BCRYPT_COST, build_test_auth_service
from tests.helpers.engine import mock_engine_context


@pytest.fixture(autouse=True)
def _cheap_default_hasher(monkeypatch):
    """Force the module-level `hash_password` / `verify_password` shims
    to use the test cost factor. They go through `_get_default_hasher`
    which lazily constructs a `BcryptHasher` with the library default
    cost (~160ms/hash); for tests that use those shims directly
    (`test_types.TestPasswordHashing`) the saving is the whole bcrypt
    bill for the file. Production code never sees this monkeypatch
    because it imports the module fresh outside the test session.
    """
    cheap = BcryptHasher(ValidationRules.default(), cost=TEST_BCRYPT_COST)
    monkeypatch.setattr(_hashers_module, "_default_hasher", cheap)


# Centralized test credentials. Any test that needs "a user" without
# caring about the specific values goes through these; tests that
# exercise specific validation paths (bad password, reserved username,
# etc.) continue to pass their own strings.
DEFAULT_USERNAME = "alice"
DEFAULT_PASSWORD = "password123"


@pytest.fixture
async def auth_db(tmp_path: Path) -> AuthDb:
    """Return a connected :class:`AuthDb` against a fresh, migrated
    ``auth.sqlite3`` in the test's temp dir."""
    path = tmp_path / "auth.sqlite3"
    await initialize_auth_schema(path)
    db = AuthDb(path)
    await db.connect()
    yield db
    await db.close()


@contextlib.asynccontextmanager
async def _booted_credentials_app(tmp_path: Path, monkeypatch, *, max_users: str):
    monkeypatch.setenv("AUTH_MODE", "credentials")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("MAX_USERS", max_users)
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    # `vite_asset` needs a built manifest otherwise — dev-mode emits tags
    # that point at a local dev server and skip the manifest lookup, which
    # is what we need for UI-page integration tests that render templates.
    monkeypatch.setenv("VITE_DEV", "true")
    # Force bcrypt to its minimum cost factor (~0.8ms/hash vs. ~160ms at
    # the library default). The auth suite hashes ~240 passwords; without
    # this the tests spend ~85% of wall time inside bcrypt.
    monkeypatch.setenv("AUTH_BCRYPT_COST", str(TEST_BCRYPT_COST))

    ns = argparse.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(os.environ))

    with mock_engine_context():
        app = create_app(config)
        async with app.router.lifespan_context(app):
            yield app


@pytest.fixture
async def credentials_app(tmp_path: Path, monkeypatch):
    """Boot a full FastAPI app in ``AUTH_MODE=credentials`` with
    ``MAX_USERS=1`` (the common-case fixture — 99% of auth tests run
    against a single-user instance). Filesystem state is rooted at
    ``tmp_path`` and the engine pool is mocked via
    ``mock_engine_context`` so no real Stockfish binary is required.

    The lifespan context is entered here so ``_bootstrap_auth`` runs
    before any request is dispatched — ``app.state.auth.service`` and
    ``app.state.auth.db`` are guaranteed live when the fixture yields.
    """
    async with _booted_credentials_app(tmp_path, monkeypatch, max_users="1") as app:
        yield app


@pytest.fixture
async def credentials_app_multi(tmp_path: Path, monkeypatch):
    """Variant of :func:`credentials_app` with ``MAX_USERS=2`` — for
    multi-user scenarios (data isolation, per-user DB separation). The
    cap has to be lifted at boot time; monkeypatching ``MAX_USERS``
    inside a test cannot affect the already-validated
    ``config.auth.max_users``.
    """
    async with _booted_credentials_app(tmp_path, monkeypatch, max_users="2") as app:
        yield app


@pytest.fixture
async def client_credentials_mode(credentials_app: FastAPI):
    transport = ASGITransport(app=credentials_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture
async def invite_code(credentials_app: FastAPI) -> str:
    code = await credentials_app.state.auth.storage.setup.get("invite_code")
    assert code, "startup hook should have persisted an invite code"
    return code


@pytest.fixture
async def service(auth_db: AuthDb, tmp_path: Path) -> AuthService:
    """AuthService wired against the shared ``auth_db`` with production-
    default timeouts (30d max age / 7d idle). Tests that exercise session
    expiry or other time-sensitive paths use :func:`service_factory`
    instead."""
    users_dir = tmp_path / "users"
    users_dir.mkdir(exist_ok=True)
    return build_test_auth_service(auth_db=auth_db, users_dir=users_dir)


@pytest.fixture
def service_factory(auth_db: AuthDb, tmp_path: Path):
    """Callable yielding :class:`AuthService` instances with overridable
    timeouts. Used by session-expiry / idle-timeout tests where the
    production 30d/7d defaults would make the test take a month to run."""

    def _make(
        *,
        session_max_age: timedelta = timedelta(days=30),
        session_idle: timedelta = timedelta(days=7),
    ) -> AuthService:
        users_dir = tmp_path / "users"
        users_dir.mkdir(exist_ok=True)
        return build_test_auth_service(
            auth_db=auth_db,
            users_dir=users_dir,
            session_max_age=session_max_age,
            session_idle=session_idle,
        )

    return _make


async def signup_via_http(
    client: httpx.AsyncClient,
    invite: str,
    *,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
) -> httpx.Response:
    """Shared helper for HTTP-layer tests that need a registered user as
    setup. Replaces the three byte-identical ``_signup`` copies that used
    to live in ``test_setup_flow.py``, ``test_ui_pages.py``, and
    ``test_settings_credentials_mode.py``.

    Exposed as a plain function (not a fixture) so tests that previously
    called ``_signup(client, invite)`` as a top-level helper can keep the
    same call shape via ``from tests.auth.conftest import signup_via_http``."""
    return await client.post(
        "/api/auth/signup",
        json={
            "username": username,
            "password": password,
            "invite_code": invite,
        },
    )

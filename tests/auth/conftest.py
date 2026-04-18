from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.repository import SetupRepository
from blunder_tutor.auth.schema import initialize_auth_schema
from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import config_factory
from tests.helpers.engine import mock_engine_context


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


@pytest.fixture
async def credentials_app(tmp_path: Path, monkeypatch):
    """Boot a full FastAPI app in ``AUTH_MODE=credentials`` with all
    filesystem state rooted at ``tmp_path``. The engine pool is mocked
    via ``mock_engine_context`` so no real Stockfish binary is required.

    The lifespan context is entered here so ``_bootstrap_auth`` runs
    before any request is dispatched — ``app.state.auth_service`` and
    ``app.state.auth_db`` are guaranteed live when the fixture yields.
    """
    monkeypatch.setenv("AUTH_MODE", "credentials")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("MAX_USERS", "1")
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    # `vite_asset` needs a built manifest otherwise — dev-mode emits tags
    # that point at a local dev server and skip the manifest lookup, which
    # is what we need for UI-page integration tests that render templates.
    monkeypatch.setenv("VITE_DEV", "true")

    ns = argparse.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(os.environ))

    with mock_engine_context():
        app = create_app(config)
        async with app.router.lifespan_context(app):
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
    repo = SetupRepository(db=credentials_app.state.auth_db)
    code = await repo.get("invite_code")
    assert code, "startup hook should have persisted an invite code"
    return code

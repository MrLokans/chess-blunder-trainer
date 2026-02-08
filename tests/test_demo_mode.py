"""Tests for demo mode middleware and configuration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig


@pytest.fixture
def demo_config(db_path: Path) -> AppConfig:
    return AppConfig(
        username="testuser",
        engine_path="/usr/bin/stockfish",
        engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent / "templates",
        ),
        demo_mode=True,
    )


@pytest.fixture
def demo_app(demo_config: AppConfig):
    import chess
    import chess.engine

    mock_engine = MagicMock()
    mock_engine.id = {"name": "Stockfish 17", "author": "Test"}
    mock_engine.analyse = AsyncMock(
        return_value={
            "score": chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE),
            "pv": [],
        }
    )
    mock_engine.quit = AsyncMock()
    rc_future = MagicMock()
    rc_future.done.return_value = False
    mock_engine.returncode = rc_future
    mock_transport = MagicMock()

    async def mock_popen_uci(path):
        return (mock_transport, mock_engine)

    with patch("chess.engine.popen_uci", mock_popen_uci):
        fastapi_app = create_app(demo_config)
        with TestClient(fastapi_app) as client:
            yield client


BLOCKED_ENDPOINTS = [
    ("POST", "/api/setup"),
    ("POST", "/api/import/start"),
    ("POST", "/api/sync/start"),
    ("POST", "/api/analysis/start"),
    ("POST", "/api/analysis/stop/123"),
    ("DELETE", "/api/jobs/123"),
    ("POST", "/api/backfill-phases/start"),
    ("POST", "/api/backfill-eco/start"),
    ("POST", "/api/backfill-tactics/start"),
    ("POST", "/api/settings"),
    ("POST", "/api/settings/board"),
    ("POST", "/api/settings/board/reset"),
    ("POST", "/api/settings/theme/reset"),
    ("POST", "/api/settings/features"),
    ("DELETE", "/api/data/all"),
]


@pytest.mark.parametrize("method,path", BLOCKED_ENDPOINTS)
def test_demo_mode_blocks_mutations(demo_app: TestClient, method: str, path: str):
    response = demo_app.request(method, path)
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "demo_mode"


def test_demo_mode_allows_get_endpoints(demo_app: TestClient):
    response = demo_app.get("/api/jobs/html")
    assert response.status_code != 403


def test_demo_mode_allows_locale_change(demo_app: TestClient):
    response = demo_app.post("/api/settings/locale", json={"locale": "ru"})
    assert response.status_code != 403


def test_normal_mode_allows_mutations(app: TestClient):
    response = app.post("/api/settings", json={})
    # May return 422 (validation error) but NOT 403
    assert response.status_code != 403


def test_demo_mode_skips_setup_redirect(demo_app: TestClient):
    response = demo_app.get("/", follow_redirects=False)
    # Should NOT redirect to /setup
    assert response.status_code != 303 or "/setup" not in response.headers.get(
        "location", ""
    )


def test_demo_banner_present_in_html(demo_app: TestClient):
    response = demo_app.get("/")
    assert "demo-banner" in response.text


def test_normal_mode_no_demo_banner(app: TestClient):
    response = app.get("/", follow_redirects=False)
    if response.status_code == 200:
        assert "demo-banner" not in response.text

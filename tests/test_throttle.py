from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig, ThrottleConfig


@pytest.fixture
def throttled_config(db_path: Path) -> AppConfig:
    return AppConfig(
        username="testuser",
        engine_path="/usr/bin/stockfish",
        engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent / "templates",
        ),
        demo_mode=True,
        throttle=ThrottleConfig(engine_requests=3, engine_window_seconds=60),
    )


@pytest.fixture
def throttled_app(throttled_config: AppConfig):
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
        fastapi_app = create_app(throttled_config)
        with TestClient(fastapi_app) as client:
            yield client


def test_throttle_returns_429_after_limit(throttled_app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}

    for _ in range(3):
        resp = throttled_app.post("/api/analyze", json=payload)
        assert resp.status_code != 429

    resp = throttled_app.post("/api/analyze", json=payload)
    assert resp.status_code == 429


def test_throttle_shared_across_engine_endpoints(throttled_app: TestClient):
    analyze_payload = {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }

    for _ in range(3):
        throttled_app.post("/api/analyze", json=analyze_payload)

    resp = throttled_app.get("/api/puzzle")
    assert resp.status_code == 429


def test_throttle_adds_rate_limit_headers(throttled_app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}
    resp = throttled_app.post("/api/analyze", json=payload)
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers


def test_normal_mode_no_throttle(app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}
    for _ in range(10):
        resp = app.post("/api/analyze", json=payload)
        assert resp.status_code != 429

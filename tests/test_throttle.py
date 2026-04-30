from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig, ThrottleConfig
from tests.helpers.engine import make_test_client


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
    yield from make_test_client(throttled_config)


def test_throttle_returns_429_after_limit(throttled_app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}

    for _ in range(3):
        resp = throttled_app.post("/api/analyze", json=payload)
        assert resp.status_code != HTTPStatus.TOO_MANY_REQUESTS

    resp = throttled_app.post("/api/analyze", json=payload)
    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_throttle_shared_across_engine_endpoints(throttled_app: TestClient):
    analyze_payload = {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }

    for _ in range(3):
        throttled_app.post("/api/analyze", json=analyze_payload)

    resp = throttled_app.get("/api/puzzle")
    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_throttle_adds_rate_limit_headers(throttled_app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}
    resp = throttled_app.post("/api/analyze", json=payload)
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers


def test_normal_mode_no_throttle(app: TestClient):
    payload = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}
    for _ in range(10):
        resp = app.post("/api/analyze", json=payload)
        assert resp.status_code != HTTPStatus.TOO_MANY_REQUESTS

"""Shared mock engine and test client helpers."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import chess
import chess.engine
from fastapi.testclient import TestClient

from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import AppConfig


def create_mock_engine() -> tuple[MagicMock, MagicMock]:
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
    return mock_transport, mock_engine


@contextmanager
def mock_engine_context():
    mock_transport, mock_engine = create_mock_engine()

    async def mock_popen_uci(path):
        return (mock_transport, mock_engine)

    with patch("chess.engine.popen_uci", mock_popen_uci):
        yield mock_transport, mock_engine


def make_test_client(config: AppConfig) -> TestClient:
    with mock_engine_context():
        fastapi_app = create_app(config)
        with TestClient(fastapi_app) as client:
            yield client

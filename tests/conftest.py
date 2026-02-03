"""Pytest configuration and shared fixtures for tests."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository
from blunder_tutor.trainer import Trainer
from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig


@pytest.fixture
def temp_dir() -> Generator[Path]:
    """Provide a temporary directory that cleans up after the test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def db_path(temp_dir: Path) -> Path:
    path = temp_dir / "test.sqlite"
    run_migrations(path)
    return path


@pytest.fixture
def test_config(db_path: Path) -> AppConfig:
    """Provide a test configuration object.

    Note: This config uses a mock engine path. Tests that require
    an actual chess engine should skip or mock the engine.
    """
    return AppConfig(
        username="testuser",
        engine_path="/usr/bin/stockfish",  # Mock path
        engine=EngineConfig(
            path="/usr/bin/stockfish",
            depth=10,
            time_limit=1.0,
        ),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent / "templates",
        ),
    )


@pytest.fixture
async def analysis_repo(db_path: Path) -> AsyncGenerator[AnalysisRepository]:
    repo = AnalysisRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def game_repo(db_path: Path) -> AsyncGenerator[GameRepository]:
    repo = GameRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def puzzle_attempt_repo(db_path: Path) -> AsyncGenerator[PuzzleAttemptRepository]:
    repo = PuzzleAttemptRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def trainer(
    game_repo: GameRepository,
    puzzle_attempt_repo: PuzzleAttemptRepository,
    analysis_repo: AnalysisRepository,
) -> Trainer:
    return Trainer(
        games=game_repo,
        attempts=puzzle_attempt_repo,
        analysis=analysis_repo,
    )


@pytest.fixture
def app(test_config: AppConfig) -> Generator[TestClient]:
    import chess
    import chess.engine
    from unittest.mock import patch

    mock_engine = MagicMock()
    mock_engine.id = {
        "name": "Stockfish 17",
        "author": "T. Romstad, M. Costalba, J. Kiiski, G. Linscott",
    }
    mock_engine.analyse = AsyncMock(
        return_value={
            "score": chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE),
            "pv": [],
        }
    )
    mock_engine.quit = AsyncMock()
    mock_transport = MagicMock()

    async def mock_popen_uci(path):
        return (mock_transport, mock_engine)

    with patch("chess.engine.popen_uci", mock_popen_uci):
        fastapi_app = create_app(test_config)
        with TestClient(fastapi_app) as client:
            yield client


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)",
    )

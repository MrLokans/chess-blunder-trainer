"""Pytest configuration and shared fixtures for tests."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository
from blunder_tutor.trainer import Trainer
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig
from tests.helpers.engine import make_test_client


@pytest.fixture(autouse=True)
def _no_sentry_in_tests() -> None:
    """Belt-and-braces: catch any test that inadvertently initializes Sentry.

    `init_observability` short-circuits when its config is disabled (the
    default in tests, since `SENTRY_ENABLED` is unset). If this assertion
    ever trips, something is calling `sentry_sdk.init` that should not be —
    fix the source, do not suppress the assert.
    """
    assert not sentry_sdk.get_client().is_active(), (
        "Sentry client is active during a test — observability must stay "
        "off in the test suite. Check that no fixture sets SENTRY_ENABLED "
        "or SENTRY_DSN, and that init_observability is not invoked."
    )


@pytest.fixture
def temp_dir() -> Generator[Path]:
    """Provide a temporary directory that cleans up after the test."""
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        yield Path(tmp_dir_path)


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
    yield from make_test_client(test_config)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)",
    )

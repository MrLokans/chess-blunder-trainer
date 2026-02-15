"""Tests for PuzzleService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from blunder_tutor.services.analysis_service import AnalysisService, PositionAnalysis
from blunder_tutor.services.puzzle_service import PuzzleService
from blunder_tutor.trainer import BlunderPuzzle, Trainer


def _make_puzzle(**overrides) -> BlunderPuzzle:
    defaults = {
        "game_id": "g1",
        "ply": 10,
        "blunder_uci": "e2e4",
        "blunder_san": "e4",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "source": "lichess",
        "username": "testuser",
        "eval_before": 50,
        "eval_after": -200,
        "cp_loss": 250,
        "player_color": "white",
        "best_move_uci": "d2d4",
        "best_move_san": "d4",
        "best_line": "d4 Nf6 Nc3",
        "best_move_eval": 30,
        "game_phase": 1,
    }
    defaults.update(overrides)
    return BlunderPuzzle(**defaults)


def _make_analysis() -> PositionAnalysis:
    return PositionAnalysis(
        eval_cp=50,
        eval_display="+0.5",
        best_move_uci="d2d4",
        best_move_san="d4",
        best_line=["d4", "Nf6"],
    )


@pytest.fixture
def mock_trainer() -> Trainer:
    t = AsyncMock(spec=Trainer)
    return t


@pytest.fixture
def mock_analysis_service() -> AnalysisService:
    return AsyncMock(spec=AnalysisService)


@pytest.fixture
def puzzle_service(mock_trainer, mock_analysis_service) -> PuzzleService:
    return PuzzleService(trainer=mock_trainer, analysis_service=mock_analysis_service)


class TestGetPuzzleWithAnalysis:
    async def test_precomputed_best_line(
        self, puzzle_service, mock_trainer, mock_analysis_service
    ):
        puzzle = _make_puzzle()
        mock_trainer.pick_random_blunder = AsyncMock(return_value=puzzle)

        result = await puzzle_service.get_puzzle_with_analysis()

        assert result.puzzle is puzzle
        assert result.analysis.best_move_uci == "d2d4"
        assert result.analysis.best_move_san == "d4"
        assert result.analysis.best_line == ["d4", "Nf6", "Nc3"]
        mock_analysis_service.analyze_position.assert_not_called()

    async def test_no_best_line_calls_engine(
        self, puzzle_service, mock_trainer, mock_analysis_service
    ):
        puzzle = _make_puzzle(best_move_uci=None, best_move_san=None, best_line=None)
        mock_trainer.pick_random_blunder = AsyncMock(return_value=puzzle)
        engine_analysis = _make_analysis()
        mock_analysis_service.analyze_position = AsyncMock(return_value=engine_analysis)

        result = await puzzle_service.get_puzzle_with_analysis()

        assert result.puzzle is puzzle
        assert result.analysis is engine_analysis
        mock_analysis_service.analyze_position.assert_called_once_with(
            fen=puzzle.fen, player_color="white"
        )

    async def test_partial_best_data_calls_engine(
        self, puzzle_service, mock_trainer, mock_analysis_service
    ):
        puzzle = _make_puzzle(best_line=None)
        mock_trainer.pick_random_blunder = AsyncMock(return_value=puzzle)
        engine_analysis = _make_analysis()
        mock_analysis_service.analyze_position = AsyncMock(return_value=engine_analysis)

        result = await puzzle_service.get_puzzle_with_analysis()

        assert result.analysis is engine_analysis
        mock_analysis_service.analyze_position.assert_called_once()

    async def test_passes_filter_params(self, puzzle_service, mock_trainer):
        puzzle = _make_puzzle()
        mock_trainer.pick_random_blunder = AsyncMock(return_value=puzzle)

        await puzzle_service.get_puzzle_with_analysis(
            start_date="2024-01-01",
            end_date="2024-12-31",
            game_phases=[0, 1],
            tactical_patterns=[1],
            game_types=[2],
            player_colors=[0],
            difficulty_ranges=[(20, 60)],
        )

        mock_trainer.pick_random_blunder.assert_called_once_with(
            start_date="2024-01-01",
            end_date="2024-12-31",
            exclude_recently_solved=True,
            spaced_repetition_days=30,
            game_phases=[0, 1],
            tactical_patterns=[1],
            game_types=[2],
            player_colors=[0],
            difficulty_ranges=[(20, 60)],
        )


class TestGetSpecificPuzzle:
    async def test_happy_path_precomputed(
        self, puzzle_service, mock_trainer, mock_analysis_service
    ):
        puzzle = _make_puzzle()
        mock_trainer.get_specific_blunder = AsyncMock(return_value=puzzle)

        result = await puzzle_service.get_specific_puzzle("g1", 10)

        assert result.puzzle is puzzle
        assert result.analysis.best_move_uci == "d2d4"
        assert result.analysis.best_line == ["d4", "Nf6", "Nc3"]
        mock_analysis_service.analyze_position.assert_not_called()

    async def test_no_best_line_calls_engine(
        self, puzzle_service, mock_trainer, mock_analysis_service
    ):
        puzzle = _make_puzzle(best_move_uci=None, best_move_san=None, best_line=None)
        mock_trainer.get_specific_blunder = AsyncMock(return_value=puzzle)
        engine_analysis = _make_analysis()
        mock_analysis_service.analyze_position = AsyncMock(return_value=engine_analysis)

        result = await puzzle_service.get_specific_puzzle("g1", 10)

        assert result.analysis is engine_analysis
        mock_analysis_service.analyze_position.assert_called_once_with(
            fen=puzzle.fen, player_color="white"
        )

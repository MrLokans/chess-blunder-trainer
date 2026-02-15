"""Tests for Trainer.get_specific_blunder."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from blunder_tutor.trainer import Trainer
from tests.helpers.factories import make_mock_game


@pytest.fixture
def mock_trainer(trainer: Trainer) -> Trainer:
    trainer.games.get_game = AsyncMock(
        return_value={"source": "lichess", "username": "testuser"}
    )
    return trainer


class TestGetSpecificBlunder:
    async def test_happy_path(self, mock_trainer: Trainer):
        mock_trainer.analysis.get_move_analysis = AsyncMock(
            return_value={
                "game_id": "g1",
                "ply": 5,
                "player": 0,
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 50,
                "eval_after": -200,
                "cp_loss": 250,
                "best_move_uci": "d2d4",
                "best_move_san": "d4",
                "best_line": "d4 Nf6",
                "best_move_eval": 30,
                "game_phase": 0,
                "tactical_pattern": 1,
                "tactical_reason": "fork",
                "difficulty": 45,
                "missed_mate_depth": None,
            }
        )
        mock_trainer.games.load_game = AsyncMock(
            return_value=make_mock_game(headers={"Site": "https://lichess.org/abc"})
        )

        puzzle = await mock_trainer.get_specific_blunder("g1", 5)

        assert puzzle.game_id == "g1"
        assert puzzle.ply == 5
        assert puzzle.blunder_uci == "e2e4"
        assert puzzle.player_color == "white"
        assert puzzle.best_move_uci == "d2d4"
        assert puzzle.game_phase == 0
        assert puzzle.tactical_pattern == 1
        assert puzzle.difficulty == 45
        assert puzzle.source == "lichess"
        assert puzzle.username == "testuser"
        assert puzzle.game_url == "https://lichess.org/abc"
        assert puzzle.fen is not None

    async def test_analysis_not_found_raises(self, mock_trainer: Trainer):
        mock_trainer.analysis.get_move_analysis = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="No analysis found"):
            await mock_trainer.get_specific_blunder("g1", 99)

    async def test_black_player(self, mock_trainer: Trainer):
        mock_trainer.analysis.get_move_analysis = AsyncMock(
            return_value={
                "game_id": "g1",
                "ply": 6,
                "player": 1,
                "uci": "e7e5",
                "san": "e5",
                "eval_before": -50,
                "eval_after": 200,
                "cp_loss": 250,
                "best_move_uci": None,
                "best_move_san": None,
                "best_line": None,
                "best_move_eval": None,
                "game_phase": 1,
                "tactical_pattern": None,
                "tactical_reason": None,
                "difficulty": None,
                "missed_mate_depth": None,
            }
        )
        mock_trainer.games.load_game = AsyncMock(return_value=make_mock_game())

        puzzle = await mock_trainer.get_specific_blunder("g1", 6)

        assert puzzle.player_color == "black"
        assert puzzle.best_move_uci is None

    async def test_no_game_metadata(self, mock_trainer: Trainer):
        mock_trainer.analysis.get_move_analysis = AsyncMock(
            return_value={
                "game_id": "g1",
                "ply": 5,
                "player": 0,
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 50,
                "eval_after": -200,
                "cp_loss": 250,
                "best_move_uci": None,
                "best_move_san": None,
                "best_line": None,
                "best_move_eval": None,
                "game_phase": None,
                "tactical_pattern": None,
                "tactical_reason": None,
                "difficulty": None,
                "missed_mate_depth": None,
            }
        )
        mock_trainer.games.load_game = AsyncMock(return_value=make_mock_game())
        mock_trainer.games.get_game = AsyncMock(return_value=None)

        puzzle = await mock_trainer.get_specific_blunder("g1", 5)

        assert puzzle.source == "any"
        assert puzzle.username == ""

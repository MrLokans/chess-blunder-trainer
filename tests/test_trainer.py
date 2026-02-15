from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from tests.helpers.factories import make_blunder, make_mock_game


class TestPickRandomBlunder:
    async def test_pick_blunder_basic(self, trainer):
        trainer.games.get_all_game_side_map = AsyncMock(return_value={"game1": 0})
        trainer.attempts.get_recently_solved_puzzles = AsyncMock(return_value=set())
        trainer.analysis.fetch_blunders_with_tactics = AsyncMock(
            return_value=[
                make_blunder(
                    game_id="game1",
                    eval_before=50,
                    eval_after=-100,
                    cp_loss=150,
                    game_phase=None,
                )
            ]
        )
        trainer.games.load_game = AsyncMock(
            return_value=make_mock_game(headers={"Site": "https://lichess.org/abc123"})
        )

        puzzle = await trainer.pick_random_blunder()

        assert puzzle.game_id == "game1"
        assert puzzle.ply == 10
        assert puzzle.blunder_uci == "e2e4"
        assert puzzle.player_color == "white"
        assert puzzle.game_url == "https://lichess.org/abc123"

    async def test_no_games_found(self, trainer):
        trainer.games.get_all_game_side_map = AsyncMock(return_value={})

        with pytest.raises(ValueError, match="No games found"):
            await trainer.pick_random_blunder()

    async def test_no_blunders_found(self, trainer):
        trainer.games.get_all_game_side_map = AsyncMock(return_value={"game1": 0})
        trainer.analysis.fetch_blunders_with_tactics = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No blunders found"):
            await trainer.pick_random_blunder()

    async def test_filters_mate_situations(self, trainer):
        trainer.games.get_all_game_side_map = AsyncMock(return_value={"game1": 0})
        trainer.attempts.get_recently_solved_puzzles = AsyncMock(return_value=set())
        trainer.analysis.fetch_blunders_with_tactics = AsyncMock(
            return_value=[
                make_blunder(
                    game_id="game1",
                    ply=5,
                    eval_before=95000,
                    eval_after=100,
                    cp_loss=150,
                    best_move_uci=None,
                    best_move_san=None,
                    best_line=None,
                    best_move_eval=None,
                    game_phase=None,
                ),
                make_blunder(
                    game_id="game1",
                    uci="d2d4",
                    san="d4",
                    eval_before=50,
                    eval_after=-100,
                    cp_loss=150,
                    best_move_uci="e2e4",
                    best_move_san="e4",
                    best_line="e4 e5",
                    game_phase=None,
                ),
            ]
        )
        trainer.games.load_game = AsyncMock(return_value=make_mock_game())

        puzzle = await trainer.pick_random_blunder()

        assert puzzle.ply == 10
        assert puzzle.blunder_uci == "d2d4"

from __future__ import annotations

from unittest.mock import MagicMock

import chess
import chess.pgn
import pytest

from blunder_tutor.trainer import BlunderPuzzle


class TestBlunderPuzzle:
    def test_create_puzzle(self):
        puzzle = BlunderPuzzle(
            game_id="test123",
            ply=10,
            blunder_uci="e2e4",
            blunder_san="e4",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            source="test",
            username="testuser",
            eval_before=50,
            eval_after=-100,
            cp_loss=150,
            player_color="white",
            best_move_uci="d2d4",
            best_move_san="d4",
            best_line="d4 Nf6 c4",
            best_move_eval=30,
        )

        assert puzzle.game_id == "test123"
        assert puzzle.ply == 10
        assert puzzle.blunder_uci == "e2e4"
        assert puzzle.eval_before == 50
        assert puzzle.eval_after == -100
        assert puzzle.cp_loss == 150
        assert puzzle.player_color == "white"
        assert puzzle.best_move_uci == "d2d4"
        assert puzzle.best_move_san == "d4"


class TestPickRandomBlunder:
    def test_pick_blunder_basic(self, trainer):
        # Mock game repository methods
        trainer.games.get_username_side_map = MagicMock(
            return_value={"game1": 0}  # white
        )

        # Mock puzzle attempt repository
        trainer.attempts.get_recently_solved_puzzles = MagicMock(return_value=set())

        # Mock analysis repository
        trainer.analysis.fetch_blunders = MagicMock(
            return_value=[
                {
                    "game_id": "game1",
                    "ply": 10,
                    "player": 0,  # white
                    "uci": "e2e4",
                    "san": "e4",
                    "eval_before": 50,
                    "eval_after": -100,
                    "cp_loss": 150,
                    "best_move_uci": "d2d4",
                    "best_move_san": "d4",
                    "best_line": "d4 Nf6",
                    "best_move_eval": 30,
                }
            ]
        )

        # Mock game with enough moves for ply 10
        mock_game = MagicMock(spec=chess.pgn.Game)
        mock_board = chess.Board()
        mock_game.board.return_value = mock_board
        # Generate 10 moves (5 white, 5 black)
        moves = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
            chess.Move.from_uci("g1f3"),
            chess.Move.from_uci("b8c6"),
            chess.Move.from_uci("f1c4"),
            chess.Move.from_uci("g8f6"),
            chess.Move.from_uci("d2d3"),
            chess.Move.from_uci("f8c5"),
            chess.Move.from_uci("c2c3"),
            chess.Move.from_uci("d7d6"),
        ]
        mock_game.mainline_moves.return_value = moves
        trainer.games.load_game = MagicMock(return_value=mock_game)

        puzzle = trainer.pick_random_blunder("testuser")

        assert puzzle.game_id == "game1"
        assert puzzle.ply == 10
        assert puzzle.blunder_uci == "e2e4"
        assert puzzle.player_color == "white"
        assert puzzle.username == "testuser"

    def test_no_games_found(self, trainer):
        # No games found for user
        trainer.games.get_username_side_map = MagicMock(return_value={})

        with pytest.raises(ValueError, match="No games found"):
            trainer.pick_random_blunder("testuser")

    def test_no_blunders_found(self, trainer):
        # Mock get_username_side_map
        trainer.games.get_username_side_map = MagicMock(
            return_value={"game1": 0}  # white
        )

        # No blunders
        trainer.analysis.fetch_blunders = MagicMock(return_value=[])

        with pytest.raises(ValueError, match="No blunders found"):
            trainer.pick_random_blunder("testuser")

    def test_filters_mate_situations(self, trainer):
        # Mock game repository
        trainer.games.get_username_side_map = MagicMock(
            return_value={"game1": 0}  # white
        )

        # Mock puzzle attempt repository
        trainer.attempts.get_recently_solved_puzzles = MagicMock(return_value=set())

        # One real blunder, one mate situation (should be filtered)
        trainer.analysis.fetch_blunders = MagicMock(
            return_value=[
                {
                    "game_id": "game1",
                    "ply": 5,
                    "player": 0,
                    "uci": "e2e4",
                    "san": "e4",
                    "eval_before": 95000,  # Mate score
                    "eval_after": 100,
                    "cp_loss": 150,
                    "best_move_uci": None,
                    "best_move_san": None,
                    "best_line": None,
                    "best_move_eval": None,
                },
                {
                    "game_id": "game1",
                    "ply": 10,
                    "player": 0,
                    "uci": "d2d4",
                    "san": "d4",
                    "eval_before": 50,
                    "eval_after": -100,
                    "cp_loss": 150,
                    "best_move_uci": "e2e4",
                    "best_move_san": "e4",
                    "best_line": "e4 e5",
                    "best_move_eval": 30,
                },
            ]
        )

        mock_game = MagicMock(spec=chess.pgn.Game)
        mock_board = chess.Board()
        mock_game.board.return_value = mock_board
        # Generate enough moves for ply 10
        moves = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
            chess.Move.from_uci("g1f3"),
            chess.Move.from_uci("b8c6"),
            chess.Move.from_uci("f1c4"),
            chess.Move.from_uci("g8f6"),
            chess.Move.from_uci("d2d3"),
            chess.Move.from_uci("f8c5"),
            chess.Move.from_uci("c2c3"),
            chess.Move.from_uci("d7d6"),
        ]
        mock_game.mainline_moves.return_value = moves
        trainer.games.load_game = MagicMock(return_value=mock_game)

        puzzle = trainer.pick_random_blunder("testuser")

        # Should get the second blunder (non-mate situation)
        assert puzzle.ply == 10
        assert puzzle.blunder_uci == "d2d4"

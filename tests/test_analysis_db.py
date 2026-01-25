from __future__ import annotations

import tempfile
from pathlib import Path

from blunder_tutor.analysis.db import ensure_schema
from blunder_tutor.constants import CLASSIFICATION_BLUNDER


class TestEnsureSchema:
    def test_create_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.sqlite"

            ensure_schema(db_path)

            assert db_path.exists()
            # Schema creation is idempotent
            ensure_schema(db_path)


class TestAnalysisExists:
    def test_analysis_not_exists(self, analysis_repo):
        exists = analysis_repo.analysis_exists("game123")
        assert not exists

    def test_analysis_exists_after_write(self, analysis_repo):
        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test.pgn",
            analyzed_at="2023-12-25T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=[],
        )

        exists = analysis_repo.analysis_exists("game123")
        assert exists


class TestWriteAnalysis:
    def test_write_basic_analysis(self, analysis_repo):
        moves = [
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,
            },
            {
                "ply": 2,
                "move_number": 1,
                "player": "black",
                "uci": "e7e5",
                "san": "e5",
                "eval_before": -30,
                "eval_after": 50,
                "delta": -80,
                "cp_loss": 80,
                "classification": 1,
            },
        ]

        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test.pgn",
            analyzed_at="2023-12-25T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=moves,
        )
        assert analysis_repo.analysis_exists("game123")

    def test_write_replaces_existing(self, analysis_repo):
        moves1 = [
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,
            }
        ]

        moves2 = [
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "d2d4",
                "san": "d4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,
            }
        ]

        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test1.pgn",
            analyzed_at="2023-12-25T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=moves1,
        )

        # Write second analysis (should replace)
        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test2.pgn",
            analyzed_at="2023-12-26T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=moves2,
        )

        game_moves = analysis_repo.fetch_moves("game123")
        assert len(game_moves) == 1
        assert game_moves[0]["uci"] == "d2d4"


class TestFetchBlunders:
    def test_fetch_empty(self, analysis_repo):
        blunders = analysis_repo.fetch_blunders()
        assert blunders == []

    def test_fetch_only_blunders(self, analysis_repo):
        moves = [
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,  # Normal move
            },
            {
                "ply": 2,
                "move_number": 1,
                "player": "black",
                "uci": "e7e6",
                "san": "e6",
                "eval_before": -30,
                "eval_after": -230,
                "delta": 200,
                "cp_loss": 200,
                "classification": CLASSIFICATION_BLUNDER,  # Blunder
            },
            {
                "ply": 3,
                "move_number": 2,
                "player": "white",
                "uci": "d2d4",
                "san": "d4",
                "eval_before": 230,
                "eval_after": 150,
                "delta": 80,
                "cp_loss": 80,
                "classification": 1,  # Inaccuracy
            },
        ]

        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test.pgn",
            analyzed_at="2023-12-25T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=moves,
        )

        blunders = analysis_repo.fetch_blunders()
        assert len(blunders) == 1
        assert blunders[0]["uci"] == "e7e6"
        assert blunders[0]["cp_loss"] == 200


class TestFetchGameMoves:
    def test_fetch_game_moves(self, analysis_repo):
        moves = [
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,
            },
            {
                "ply": 2,
                "move_number": 1,
                "player": "black",
                "uci": "e7e5",
                "san": "e5",
                "eval_before": -30,
                "eval_after": -20,
                "delta": -10,
                "cp_loss": 0,
                "classification": 0,
            },
        ]

        analysis_repo.write_analysis(
            game_id="game123",
            pgn_path="/tmp/test.pgn",
            analyzed_at="2023-12-25T00:00:00Z",
            engine_path="/usr/bin/stockfish",
            depth=14,
            time_limit=None,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=moves,
        )

        game_moves = analysis_repo.fetch_moves("game123")
        assert len(game_moves) == 2
        assert game_moves[0]["uci"] == "e2e4"
        assert game_moves[1]["uci"] == "e7e5"

    def test_fetch_nonexistent_game(self, analysis_repo):
        game_moves = analysis_repo.fetch_moves("nonexistent")
        assert game_moves == []

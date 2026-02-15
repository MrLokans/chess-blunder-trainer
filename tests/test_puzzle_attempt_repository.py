"""Tests for PuzzleAttemptRepository."""

from __future__ import annotations

import pytest

from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository


class TestGetLastCorrectAttempt:
    async def test_not_found(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        result = await puzzle_attempt_repo.get_last_correct_attempt("g1", 5, "local")
        assert result is None

    async def test_only_incorrect_returns_none(
        self, puzzle_attempt_repo: PuzzleAttemptRepository
    ):
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=False)
        result = await puzzle_attempt_repo.get_last_correct_attempt("g1", 5, "local")
        assert result is None

    async def test_returns_correct_attempt(
        self, puzzle_attempt_repo: PuzzleAttemptRepository
    ):
        await puzzle_attempt_repo.record_attempt(
            "g1", 5, was_correct=True, user_move_uci="e2e4"
        )
        result = await puzzle_attempt_repo.get_last_correct_attempt("g1", 5, "local")
        assert result is not None
        assert result["was_correct"] is True
        assert result["game_id"] == "g1"
        assert result["ply"] == 5
        assert result["user_move_uci"] == "e2e4"

    async def test_returns_most_recent(
        self, puzzle_attempt_repo: PuzzleAttemptRepository
    ):
        await puzzle_attempt_repo.record_attempt(
            "g1", 5, was_correct=True, user_move_uci="e2e4"
        )
        await puzzle_attempt_repo.record_attempt(
            "g1", 5, was_correct=True, user_move_uci="d2d4"
        )
        result = await puzzle_attempt_repo.get_last_correct_attempt("g1", 5, "local")
        assert result["user_move_uci"] == "d2d4"


class TestGetPuzzleStats:
    async def test_no_attempts(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        stats = await puzzle_attempt_repo.get_puzzle_stats("g1", 5, "local")
        assert stats["total_attempts"] == 0
        assert stats["correct_attempts"] == 0
        assert stats["incorrect_attempts"] == 0
        assert stats["last_correct_at"] is None

    async def test_mixed_attempts(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=False)
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=True)
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=False)
        stats = await puzzle_attempt_repo.get_puzzle_stats("g1", 5, "local")
        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 1
        assert stats["incorrect_attempts"] == 2
        assert stats["last_correct_at"] is not None


class TestGetUserStats:
    async def test_empty(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        stats = await puzzle_attempt_repo.get_user_stats()
        assert stats["total_attempts"] == 0
        assert stats["accuracy"] == 0.0
        assert stats["unique_puzzles"] == 0

    async def test_with_data(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=True)
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=False)
        await puzzle_attempt_repo.record_attempt("g2", 10, was_correct=True)
        stats = await puzzle_attempt_repo.get_user_stats()
        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 2
        assert stats["incorrect_attempts"] == 1
        assert stats["unique_puzzles"] == 2
        assert stats["accuracy"] == pytest.approx(66.7, abs=0.1)


class TestGetRecentlySolvedPuzzles:
    async def test_empty(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        result = await puzzle_attempt_repo.get_recently_solved_puzzles()
        assert result == set()

    async def test_returns_correct_only(
        self, puzzle_attempt_repo: PuzzleAttemptRepository
    ):
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=True)
        await puzzle_attempt_repo.record_attempt("g1", 10, was_correct=False)
        result = await puzzle_attempt_repo.get_recently_solved_puzzles()
        assert ("g1", 5) in result
        assert ("g1", 10) not in result


class TestGetFailureRatesByPattern:
    async def test_no_data(self, puzzle_attempt_repo: PuzzleAttemptRepository):
        result = await puzzle_attempt_repo.get_failure_rates_by_pattern()
        assert result == {}

    async def test_with_patterns(
        self,
        puzzle_attempt_repo: PuzzleAttemptRepository,
        analysis_repo: AnalysisRepository,
    ):
        await analysis_repo.write_analysis(
            game_id="g1",
            pgn_path="",
            analyzed_at="2025-01-01",
            engine_path="",
            depth=20,
            time_limit=1.0,
            thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
            moves=[
                {
                    "ply": 5,
                    "move_number": 3,
                    "player": "white",
                    "uci": "e2e4",
                    "san": "e4",
                    "eval_before": 50,
                    "eval_after": -200,
                    "delta": -250,
                    "cp_loss": 250,
                    "classification": 3,
                    "tactical_pattern": 1,
                },
                {
                    "ply": 10,
                    "move_number": 5,
                    "player": "white",
                    "uci": "d2d4",
                    "san": "d4",
                    "eval_before": 0,
                    "eval_after": -300,
                    "delta": -300,
                    "cp_loss": 300,
                    "classification": 3,
                    "tactical_pattern": 2,
                },
            ],
        )
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=False)
        await puzzle_attempt_repo.record_attempt("g1", 5, was_correct=True)
        await puzzle_attempt_repo.record_attempt("g1", 10, was_correct=False)

        result = await puzzle_attempt_repo.get_failure_rates_by_pattern()
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(1.0)

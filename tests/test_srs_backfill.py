from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "migration_011",
    Path(__file__).parent.parent / "alembic" / "versions" / "011_add_srs_cards.py",
)
_migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migration)
BACKFILL_SQL = _migration.BACKFILL_SQL

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE puzzle_attempts (
            game_id TEXT, ply INTEGER, username TEXT,
            was_correct INTEGER, user_move_uci TEXT,
            best_move_uci TEXT, attempted_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE srs_cards (
            game_id TEXT NOT NULL, ply INTEGER NOT NULL,
            rung INTEGER NOT NULL DEFAULT 0,
            state INTEGER NOT NULL DEFAULT 0,
            due_at TEXT NOT NULL, enrolled_at TEXT NOT NULL,
            last_reviewed_at TEXT,
            total_failures INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (game_id, ply)
        )
        """
    )
    return conn


def _attempt(
    conn: sqlite3.Connection,
    game_id: str,
    ply: int,
    correct: bool,
    days_ago: int,
) -> None:
    conn.execute(
        "INSERT INTO puzzle_attempts VALUES (?, ?, 'local', ?, NULL, NULL, ?)",
        (
            game_id,
            ply,
            1 if correct else 0,
            (NOW - timedelta(days=days_ago)).isoformat(),
        ),
    )


def _backfill_result(
    attempts: list[tuple[str, int, bool, int]],
) -> list[tuple]:
    with closing(_make_db()) as conn:
        for game_id, ply, correct, days_ago in attempts:
            _attempt(conn, game_id, ply, correct=correct, days_ago=days_ago)
        params = {
            "now": NOW.isoformat(),
            "due_at": NOW.isoformat(),
            "cutoff": (NOW - timedelta(days=60)).isoformat(),
        }
        conn.execute(BACKFILL_SQL, params)
        return conn.execute(
            """
            SELECT game_id, ply, rung, state, total_failures
            FROM srs_cards ORDER BY game_id
            """
        ).fetchall()


class TestBackfill:
    def test_latest_failure_within_window_enrolls(self):
        rows = _backfill_result([("g1", 10, False, 5)])
        assert rows == [("g1", 10, 0, 0, 1)]

    def test_latest_attempt_correct_not_enrolled(self):
        rows = _backfill_result([("g1", 10, False, 10), ("g1", 10, True, 5)])
        assert rows == []

    def test_failure_older_than_window_not_enrolled(self):
        assert _backfill_result([("g1", 10, False, 90)]) == []

    def test_total_failures_counts_lifetime(self):
        rows = _backfill_result([("g1", 10, False, 90), ("g1", 10, False, 5)])
        assert rows == [("g1", 10, 0, 0, 2)]

    def test_independent_puzzles_enroll_separately(self):
        rows = _backfill_result(
            [("g1", 10, False, 5), ("g2", 20, True, 5), ("g3", 30, False, 3)]
        )
        assert rows == [("g1", 10, 0, 0, 1), ("g3", 30, 0, 0, 1)]

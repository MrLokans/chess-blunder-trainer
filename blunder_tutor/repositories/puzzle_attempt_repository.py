from __future__ import annotations

from datetime import datetime, timedelta

from blunder_tutor.repositories.base import BaseDbRepository


class PuzzleAttemptRepository(BaseDbRepository):
    def record_attempt(
        self,
        game_id: str,
        ply: int,
        username: str,
        was_correct: bool,
        user_move_uci: str | None = None,
        best_move_uci: str | None = None,
    ) -> None:
        attempted_at = datetime.utcnow().isoformat()

        conn = self.connection
        conn.execute(
            """
            INSERT INTO puzzle_attempts (
                game_id, ply, username, was_correct,
                user_move_uci, best_move_uci, attempted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                ply,
                username,
                1 if was_correct else 0,
                user_move_uci,
                best_move_uci,
                attempted_at,
            ),
        )
        conn.commit()

    def get_last_correct_attempt(
        self, game_id: str, ply: int, username: str
    ) -> dict[str, object] | None:
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT attempt_id, game_id, ply, username, was_correct,
                       user_move_uci, best_move_uci, attempted_at
                FROM puzzle_attempts
                WHERE game_id = ? AND ply = ? AND username = ? AND was_correct = 1
                ORDER BY attempted_at DESC
                LIMIT 1
                """,
                (game_id, ply, username),
            ).fetchone()

            if not row:
                return None

            return {
                "attempt_id": row[0],
                "game_id": row[1],
                "ply": row[2],
                "username": row[3],
                "was_correct": bool(row[4]),
                "user_move_uci": row[5],
                "best_move_uci": row[6],
                "attempted_at": row[7],
            }

    def get_recently_solved_puzzles(
        self, username: str, days: int = 30
    ) -> set[tuple[str, int]]:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        with self.connection as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT game_id, ply
                FROM puzzle_attempts
                WHERE username = ? AND was_correct = 1 AND attempted_at >= ?
                """,
                (username, cutoff_date),
            ).fetchall()

        return {(row[0], row[1]) for row in rows}

    def get_puzzle_stats(
        self, game_id: str, ply: int, username: str
    ) -> dict[str, object]:
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_attempts,
                    MAX(CASE WHEN was_correct = 1 THEN attempted_at ELSE NULL END) as last_correct_at
                FROM puzzle_attempts
                WHERE game_id = ? AND ply = ? AND username = ?
                """,
                (game_id, ply, username),
            ).fetchone()

            if not row or row[0] == 0:
                return {
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "incorrect_attempts": 0,
                    "last_correct_at": None,
                }

            return {
                "total_attempts": row[0],
                "correct_attempts": row[1] or 0,
                "incorrect_attempts": row[0] - (row[1] or 0),
                "last_correct_at": row[2],
            }

    def get_user_stats(self, username: str) -> dict[str, object]:
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_attempts,
                    COUNT(DISTINCT game_id || '-' || ply) as unique_puzzles
                FROM puzzle_attempts
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

            if not row or row[0] == 0:
                return {
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "incorrect_attempts": 0,
                    "unique_puzzles": 0,
                    "accuracy": 0.0,
                }

            total = row[0]
            correct = row[1] or 0

            return {
                "total_attempts": total,
                "correct_attempts": correct,
                "incorrect_attempts": total - correct,
                "unique_puzzles": row[2] or 0,
                "accuracy": round((correct / total * 100), 1) if total > 0 else 0.0,
            }

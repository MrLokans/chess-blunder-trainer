from __future__ import annotations

from datetime import timedelta

from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.time import now_iso, utcnow


class PuzzleAttemptRepository(BaseDbRepository):
    async def record_attempt(
        self,
        game_id: str,
        ply: int,
        was_correct: bool,
        user_move_uci: str | None = None,
        best_move_uci: str | None = None,
    ) -> None:
        attempted_at = now_iso()

        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT INTO puzzle_attempts (
                    game_id, ply, username, was_correct,
                    user_move_uci, best_move_uci, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    ply,
                    "local",
                    1 if was_correct else 0,
                    user_move_uci,
                    best_move_uci,
                    attempted_at,
                ),
            )

    async def get_last_correct_attempt(
        self, game_id: str, ply: int, username: str
    ) -> dict[str, object] | None:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT attempt_id, game_id, ply, username, was_correct,
                   user_move_uci, best_move_uci, attempted_at
            FROM puzzle_attempts
            WHERE game_id = ? AND ply = ? AND username = ? AND was_correct = 1
            ORDER BY attempted_at DESC
            LIMIT 1
            """,
            (game_id, ply, username),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        return {**dict(row), "was_correct": bool(row["was_correct"])}

    async def get_recently_solved_puzzles(self, days: int = 30) -> set[tuple[str, int]]:
        cutoff_date = (utcnow() - timedelta(days=days)).isoformat()

        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT DISTINCT game_id, ply
            FROM puzzle_attempts
            WHERE was_correct = 1 AND attempted_at >= ?
            """,
            (cutoff_date,),
        ) as cursor:
            rows = await cursor.fetchall()

        return {(row["game_id"], row["ply"]) for row in rows}

    async def get_puzzle_stats(
        self, game_id: str, ply: int, username: str
    ) -> dict[str, object]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_attempts,
                MAX(CASE WHEN was_correct = 1 THEN attempted_at ELSE NULL END) as last_correct_at
            FROM puzzle_attempts
            WHERE game_id = ? AND ply = ? AND username = ?
            """,
            (game_id, ply, username),
        ) as cursor:
            row = await cursor.fetchone()

        if not row or row["total_attempts"] == 0:
            return {
                "total_attempts": 0,
                "correct_attempts": 0,
                "incorrect_attempts": 0,
                "last_correct_at": None,
            }

        total = row["total_attempts"]
        correct = row["correct_attempts"] or 0
        return {
            "total_attempts": total,
            "correct_attempts": correct,
            "incorrect_attempts": total - correct,
            "last_correct_at": row["last_correct_at"],
        }

    async def get_user_stats(self) -> dict[str, object]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_attempts,
                COUNT(DISTINCT game_id || '-' || ply) as unique_puzzles
            FROM puzzle_attempts
            """
        ) as cursor:
            row = await cursor.fetchone()

        if not row or row["total_attempts"] == 0:
            return {
                "total_attempts": 0,
                "correct_attempts": 0,
                "incorrect_attempts": 0,
                "unique_puzzles": 0,
                "accuracy": 0.0,
            }

        total = row["total_attempts"]
        correct = row["correct_attempts"] or 0

        return {
            "total_attempts": total,
            "correct_attempts": correct,
            "incorrect_attempts": total - correct,
            "unique_puzzles": row["unique_puzzles"] or 0,
            "accuracy": round((correct / total * 100), 1) if total > 0 else 0.0,
        }

    async def get_failure_rates_by_pattern(self) -> dict[int | None, float]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT am.tactical_pattern,
                   COUNT(*) as attempts,
                   SUM(CASE WHEN pa.was_correct = 0 THEN 1 ELSE 0 END) as failures
            FROM puzzle_attempts pa
            JOIN analysis_moves am ON pa.game_id = am.game_id AND pa.ply = am.ply
            GROUP BY am.tactical_pattern
            """
        ) as cursor:
            rows = await cursor.fetchall()

        return {
            row["tactical_pattern"]: (
                row["failures"] / row["attempts"] if row["attempts"] > 0 else 0.0
            )
            for row in rows
        }

    async def get_daily_attempt_counts(
        self, days: int = 365
    ) -> dict[str, dict[str, int]]:
        cutoff_date = (utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                DATE(attempted_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM puzzle_attempts
            WHERE DATE(attempted_at) >= ?
            GROUP BY DATE(attempted_at)
            ORDER BY date
            """,
            (cutoff_date,),
        ) as cursor:
            rows = await cursor.fetchall()

        return {
            row["date"]: {
                "total": row["total"],
                "correct": row["correct"] or 0,
                "incorrect": row["total"] - (row["correct"] or 0),
            }
            for row in rows
        }

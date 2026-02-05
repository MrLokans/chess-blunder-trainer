from __future__ import annotations

from datetime import datetime, timedelta

from blunder_tutor.repositories.base import BaseDbRepository


class PuzzleAttemptRepository(BaseDbRepository):
    async def record_attempt(
        self,
        game_id: str,
        ply: int,
        username: str,
        was_correct: bool,
        user_move_uci: str | None = None,
        best_move_uci: str | None = None,
    ) -> None:
        attempted_at = datetime.utcnow().isoformat()

        conn = await self.get_connection()
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
                username,
                1 if was_correct else 0,
                user_move_uci,
                best_move_uci,
                attempted_at,
            ),
        )
        await conn.commit()

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

    async def get_recently_solved_puzzles(
        self, username: str, days: int = 30
    ) -> set[tuple[str, int]]:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT DISTINCT game_id, ply
            FROM puzzle_attempts
            WHERE username = ? AND was_correct = 1 AND attempted_at >= ?
            """,
            (username, cutoff_date),
        ) as cursor:
            rows = await cursor.fetchall()

        return {(row[0], row[1]) for row in rows}

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

    async def get_user_stats(self, username: str) -> dict[str, object]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_attempts,
                COUNT(DISTINCT game_id || '-' || ply) as unique_puzzles
            FROM puzzle_attempts
            WHERE username = ?
            """,
            (username,),
        ) as cursor:
            row = await cursor.fetchone()

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

    async def get_daily_attempt_counts(
        self, username: str, days: int = 365
    ) -> dict[str, dict[str, int]]:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                DATE(attempted_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM puzzle_attempts
            WHERE username = ? AND DATE(attempted_at) >= ?
            GROUP BY DATE(attempted_at)
            ORDER BY date
            """,
            (username, cutoff_date),
        ) as cursor:
            rows = await cursor.fetchall()

        return {
            row[0]: {
                "total": row[1],
                "correct": row[2] or 0,
                "incorrect": row[1] - (row[2] or 0),
            }
            for row in rows
        }

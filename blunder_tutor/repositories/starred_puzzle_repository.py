from __future__ import annotations

from datetime import datetime

from blunder_tutor.repositories.base import BaseDbRepository


class StarredPuzzleRepository(BaseDbRepository):
    async def star(self, game_id: str, ply: int, note: str | None = None) -> None:
        starred_at = datetime.utcnow().isoformat()
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO starred_puzzles (game_id, ply, starred_at, note)
                VALUES (?, ?, ?, ?)
                """,
                (game_id, ply, starred_at, note),
            )

    async def unstar(self, game_id: str, ply: int) -> bool:
        async with self.write_transaction() as conn:
            cursor = await conn.execute(
                "DELETE FROM starred_puzzles WHERE game_id = ? AND ply = ?",
                (game_id, ply),
            )
            return cursor.rowcount > 0

    async def is_starred(self, game_id: str, ply: int) -> bool:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT 1 FROM starred_puzzles WHERE game_id = ? AND ply = ?",
            (game_id, ply),
        ) as cursor:
            return await cursor.fetchone() is not None

    async def list_starred(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT sp.game_id, sp.ply, sp.starred_at, sp.note,
                   am.san, am.eval_before, am.eval_after, am.cp_loss,
                   am.game_phase, am.tactical_pattern,
                   gc.white, gc.black, gc.date, gc.source
            FROM starred_puzzles sp
            LEFT JOIN analysis_moves am ON sp.game_id = am.game_id AND sp.ply = am.ply
            LEFT JOIN game_index_cache gc ON sp.game_id = gc.game_id
            ORDER BY sp.starred_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def count_starred(self) -> int:
        conn = await self.get_connection()
        async with conn.execute("SELECT COUNT(*) FROM starred_puzzles") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def delete_all(self) -> int:
        async with self.write_transaction() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM starred_puzzles")
            count = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM starred_puzzles")
            return count

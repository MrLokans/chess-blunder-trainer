from __future__ import annotations

from blunder_tutor.repositories.base import BaseDbRepository


class TrapRepository(BaseDbRepository):
    async def save_trap_match(
        self,
        *,
        game_id: str,
        trap_id: str,
        match_type: str,
        victim_side: str,
        user_was_victim: bool,
        mistake_ply: int | None,
    ) -> None:
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO trap_matches
                    (game_id, trap_id, match_type, victim_side, user_was_victim, mistake_ply)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    trap_id,
                    match_type,
                    victim_side,
                    1 if user_was_victim else 0,
                    mistake_ply,
                ),
            )

    async def get_trap_stats(self) -> list[dict]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                trap_id,
                SUM(CASE WHEN match_type = 'entered' THEN 1 ELSE 0 END) as entered,
                SUM(CASE WHEN match_type = 'sprung' AND user_was_victim = 1 THEN 1 ELSE 0 END) as sprung,
                SUM(CASE WHEN match_type = 'executed' THEN 1 ELSE 0 END) as executed,
                COUNT(*) as total,
                MAX(created_at) as last_seen
            FROM trap_matches
            GROUP BY trap_id
            ORDER BY sprung DESC, entered DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "trap_id": row[0],
                "entered": row[1],
                "sprung": row[2],
                "executed": row[3],
                "total": row[4],
                "last_seen": row[5],
            }
            for row in rows
        ]

    async def get_trap_history(self, trap_id: str) -> list[dict]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                tm.game_id, tm.match_type, tm.user_was_victim, tm.mistake_ply,
                tm.created_at, g.white, g.black, g.result, g.date, g.source,
                g.pgn_content
            FROM trap_matches tm
            JOIN game_index_cache g ON tm.game_id = g.game_id
            WHERE tm.trap_id = ?
            ORDER BY tm.created_at DESC
            """,
            (trap_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "game_id": row[0],
                "match_type": row[1],
                "user_was_victim": bool(row[2]),
                "mistake_ply": row[3],
                "created_at": row[4],
                "white": row[5],
                "black": row[6],
                "result": row[7],
                "date": row[8],
                "source": row[9],
                "pgn_content": row[10],
            }
            for row in rows
        ]

    async def get_trap_summary(self) -> dict:
        conn = await self.get_connection()

        async with conn.execute(
            """
            SELECT
                COUNT(DISTINCT game_id) as games_with_traps,
                SUM(CASE WHEN match_type = 'sprung' AND user_was_victim = 1 THEN 1 ELSE 0 END) as total_sprung,
                SUM(CASE WHEN match_type = 'entered' THEN 1 ELSE 0 END) as total_entered,
                SUM(CASE WHEN match_type = 'executed' THEN 1 ELSE 0 END) as total_executed
            FROM trap_matches
            """
        ) as cursor:
            row = await cursor.fetchone()

        async with conn.execute(
            """
            SELECT trap_id, COUNT(*) as cnt
            FROM trap_matches
            WHERE match_type = 'sprung' AND user_was_victim = 1
            GROUP BY trap_id
            ORDER BY cnt DESC
            LIMIT 3
            """
        ) as cursor:
            top_rows = await cursor.fetchall()

        return {
            "games_with_traps": row[0] or 0,
            "total_sprung": row[1] or 0,
            "total_entered": row[2] or 0,
            "total_executed": row[3] or 0,
            "top_traps": [{"trap_id": r[0], "count": r[1]} for r in top_rows],
        }

    async def get_analyzed_game_ids_without_trap_data(self) -> list[str]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT g.game_id FROM game_index_cache g
            WHERE g.analyzed = 1
            AND NOT EXISTS (
                SELECT 1 FROM trap_matches tm WHERE tm.game_id = g.game_id
            )
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def delete_all(self) -> int:
        async with self.write_transaction() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM trap_matches")
            count = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM trap_matches")
            return count

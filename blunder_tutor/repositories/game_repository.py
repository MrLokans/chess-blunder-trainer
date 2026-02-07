from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import chess.pgn

from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.pgn_utils import load_game_from_string


class GameRepository(BaseDbRepository):
    async def get_pgn_content(self, game_id: str) -> str:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT pgn_content FROM game_index_cache WHERE game_id = ?",
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            raise FileNotFoundError(f"Game not found: {game_id}")
        return row[0]

    async def load_game(self, game_id: str) -> chess.pgn.Game:
        pgn_content = await self.get_pgn_content(game_id)
        return load_game_from_string(pgn_content)

    async def insert_games(self, games: list[dict[str, object]]) -> int:
        timestamp = datetime.utcnow().isoformat()
        inserted = 0

        async with self.write_transaction() as conn:
            for game in games:
                cursor = await conn.execute(
                    """
                    INSERT INTO game_index_cache (
                        game_id, source, username, white, black, result,
                        date, end_time_utc, time_control, pgn_content,
                        analyzed, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    ON CONFLICT(game_id) DO NOTHING
                    """,
                    (
                        game.get("id"),
                        game.get("source"),
                        game.get("username"),
                        game.get("white"),
                        game.get("black"),
                        game.get("result"),
                        game.get("date"),
                        game.get("end_time_utc"),
                        game.get("time_control"),
                        game.get("pgn_content"),
                        timestamp,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1

        return inserted

    async def get_username_side_map(
        self, username: str, source: str | None = None
    ) -> dict[str, int]:
        username_lower = username.lower()
        game_map: dict[str, int] = {}

        query = """
            SELECT game_id, white, black FROM game_index_cache
            WHERE LOWER(white) = ? OR LOWER(black) = ?
        """
        params: list[str] = [username_lower, username_lower]

        if source:
            query += " AND source = ?"
            params.append(source)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            game_id, white, black = row
            if white and white.lower() == username_lower:
                game_map[game_id] = 0
            elif black and black.lower() == username_lower:
                game_map[game_id] = 1

        return game_map

    async def list_games(
        self,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        query = """
            SELECT game_id, source, username, white, black, result,
                   date, end_time_utc, time_control, analyzed
            FROM game_index_cache
            WHERE 1=1
        """
        params: list[str | int] = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if username:
            query += " AND username = ?"
            params.append(username)

        query += " ORDER BY end_time_utc DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            async for row in cursor:
                yield {
                    "id": row[0],
                    "source": row[1],
                    "username": row[2],
                    "white": row[3],
                    "black": row[4],
                    "result": row[5],
                    "date": row[6],
                    "end_time_utc": row[7],
                    "time_control": row[8],
                    "analyzed": row[9],
                }

    async def get_game(self, game_id: str) -> dict[str, object] | None:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT game_id, source, username, white, black, result,
                   date, end_time_utc, time_control, pgn_content, analyzed
            FROM game_index_cache
            WHERE game_id = ?
            """,
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "source": row[1],
                "username": row[2],
                "white": row[3],
                "black": row[4],
                "result": row[5],
                "date": row[6],
                "end_time_utc": row[7],
                "time_control": row[8],
                "pgn_content": row[9],
                "analyzed": row[10],
            }

        return None

    async def list_games_filtered(
        self,
        source: str | None = None,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        analyzed_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[dict[str, object]], int]:
        query = """
            SELECT game_id, source, username, white, black, result,
                   date, end_time_utc, time_control, analyzed
            FROM game_index_cache
            WHERE 1=1
        """
        count_query = "SELECT COUNT(*) FROM game_index_cache WHERE 1=1"
        params: list[str | int] = []

        if source:
            query += " AND source = ?"
            count_query += " AND source = ?"
            params.append(source)

        if username:
            query += " AND username = ?"
            count_query += " AND username = ?"
            params.append(username)

        if start_date:
            query += " AND end_time_utc >= ?"
            count_query += " AND end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND end_time_utc <= ?"
            count_query += " AND end_time_utc <= ?"
            params.append(end_date)

        if analyzed_only:
            query += " AND analyzed = 1"
            count_query += " AND analyzed = 1"

        query += " ORDER BY end_time_utc DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        conn = await self.get_connection()
        count_params = [p for p in params if not isinstance(p, int) or p < 1000]
        async with conn.execute(count_query, count_params) as cursor:
            count_row = await cursor.fetchone()
            total_count = count_row[0]

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        games = [
            {
                "id": row[0],
                "source": row[1],
                "username": row[2],
                "white": row[3],
                "black": row[4],
                "result": row[5],
                "date": row[6],
                "end_time_utc": row[7],
                "time_control": row[8],
                "analyzed": row[9],
            }
            for row in rows
        ]

        return games, total_count

    async def count_games(
        self,
        source: str | None = None,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        analyzed_only: bool = False,
    ) -> int:
        query = "SELECT COUNT(*) FROM game_index_cache WHERE 1=1"
        params: list[str] = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if username:
            query += " AND username = ?"
            params.append(username)

        if start_date:
            query += " AND end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND end_time_utc <= ?"
            params.append(end_date)

        if analyzed_only:
            query += " AND analyzed = 1"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def mark_game_analyzed(self, game_id: str) -> None:
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                UPDATE game_index_cache
                SET analyzed = 1
                WHERE game_id = ?
                """,
                (game_id,),
            )

    async def list_unanalyzed_game_ids(
        self,
        source: str | None = None,
        username: str | None = None,
    ) -> list[str]:
        query = """
            SELECT game_id FROM game_index_cache
            WHERE analyzed = 0
        """
        params: list[str] = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if username:
            query += " AND username = ?"
            params.append(username)

        query += " ORDER BY end_time_utc DESC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [row[0] for row in rows]

    async def get_latest_game_time(
        self,
        source: str,
        username: str,
    ) -> datetime | None:
        """Get the end_time_utc of the most recent game for a source/username."""
        query = """
            SELECT end_time_utc FROM game_index_cache
            WHERE source = ? AND username = ?
            ORDER BY end_time_utc DESC
            LIMIT 1
        """
        conn = await self.get_connection()
        async with conn.execute(query, (source, username)) as cursor:
            row = await cursor.fetchone()

        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

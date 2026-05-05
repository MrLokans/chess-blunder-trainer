from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import chess.pgn

from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.pgn_utils import load_game_from_string
from blunder_tutor.utils.time import now_iso, parse_dt
from blunder_tutor.utils.time_control import classify_game_type

GameRow = dict[str, object]


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
        return row["pgn_content"]

    async def load_game(self, game_id: str) -> chess.pgn.Game:
        pgn_content = await self.get_pgn_content(game_id)
        return load_game_from_string(pgn_content)

    async def insert_games(
        self,
        games: list[dict[str, object]],
        *,
        profile_id: int | None = None,
    ) -> int:
        """Insert games into ``game_index_cache``.

        ``profile_id`` tags every inserted row with the owning tracked
        profile. Callers using the legacy username-pair path pass ``None``;
        rows then have ``profile_id IS NULL`` and stay reachable only by
        ``(source, username)`` denormalization.
        """
        timestamp = now_iso()
        inserted = 0

        async with self.write_transaction() as conn:
            for game in games:
                time_control = game.get("time_control")
                game_type = int(classify_game_type(time_control))
                cursor = await conn.execute(
                    """
                    INSERT INTO game_index_cache (
                        game_id, source, username, white, black, result,
                        date, end_time_utc, time_control, pgn_content,
                        analyzed, indexed_at, game_type, profile_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
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
                        time_control,
                        game.get("pgn_content"),
                        timestamp,
                        game_type,
                        profile_id,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1

        return inserted

    async def get_all_game_side_map(self) -> dict[str, int]:
        """Build a side map for every game using the stored ``username`` column."""
        game_map: dict[str, int] = {}

        conn = await self.get_connection()
        async with conn.execute(
            "SELECT game_id, username, white, black FROM game_index_cache"
        ) as cursor:
            rows = await cursor.fetchall()

        for game_id, username, white, black in rows:
            if not username:
                continue
            uname_lower = username.lower()
            if white and white.lower() == uname_lower:
                game_map[game_id] = 0
            elif black and black.lower() == uname_lower:
                game_map[game_id] = 1

        return game_map

    async def list_games(
        self,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        query = """
            SELECT game_id AS id, source, username, white, black, result,
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
                yield dict(row)

    async def get_game(self, game_id: str) -> dict[str, object] | None:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT game_id AS id, source, username, white, black, result,
                   date, end_time_utc, time_control, pgn_content, analyzed
            FROM game_index_cache
            WHERE game_id = ?
            """,
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return dict(row)

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
    ) -> tuple[list[GameRow], int]:
        query = """
            SELECT game_id AS id, source, username, white, black, result,
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

        conn = await self.get_connection()
        count_params = list(params)
        async with conn.execute(count_query, count_params) as cursor:
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        games = [dict(row) for row in rows]

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

        return [row["game_id"] for row in rows]

    async def list_rating_history_rows(
        self,
        profile_id: int,
        *,
        game_type: int | None = None,
        since: str | None = None,
    ) -> list[dict[str, object]]:
        """Project the columns needed to assemble per-game rating points.

        PGN parsing happens in the service layer so this stays a pure SQL
        projection — easy to unit-test and trivial to swap for a column-based
        query once `white_rating` / `black_rating` are denormalized.
        """
        query = """
            SELECT game_id, white, black, end_time_utc,
                   game_type, pgn_content
            FROM game_index_cache
            WHERE profile_id = ?
        """
        params: list[object] = [profile_id]

        if game_type is not None:
            query += " AND game_type = ?"
            params.append(game_type)

        if since is not None:
            query += " AND end_time_utc >= ?"
            params.append(since)

        query += " ORDER BY end_time_utc ASC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

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

        if row and row["end_time_utc"]:
            return parse_dt(row["end_time_utc"])
        return None

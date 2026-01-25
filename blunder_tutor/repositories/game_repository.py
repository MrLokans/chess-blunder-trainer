"""Repository for accessing game data and metadata."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import chess.pgn

from blunder_tutor.index import read_index
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.pgn_utils import load_game


class GameRepository(BaseDbRepository):
    def find_game_path(self, game_id: str) -> Path:
        for record in read_index(self.data_dir):
            if record.get("id") == game_id:
                return Path(str(record.get("pgn_path")))
        raise FileNotFoundError(f"Game not found in index: {game_id}")

    def load_game(self, game_id: str) -> chess.pgn.Game:
        pgn_path = self.find_game_path(game_id)
        return load_game(pgn_path)

    def get_username_side_map(
        self, username: str, source: str | None = None
    ) -> dict[str, int]:
        """Get mapping of game_id -> side (0=white, 1=black) for username.
        Returns:
            Dict mapping game_id to player side
        """
        username_lower = username.lower()
        game_map: dict[str, int] = {}

        for record in read_index(self.data_dir, source=source):
            game_id = record.get("id")
            white = str(record.get("white") or "")
            black = str(record.get("black") or "")

            if white.lower() == username_lower:
                game_map[str(game_id)] = 0
            elif black.lower() == username_lower:
                game_map[str(game_id)] = 1

        return game_map

    def list_games(
        self,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, object]]:
        for count, record in enumerate(
            read_index(self.data_dir, source=source, username=username)
        ):
            if limit is not None and count >= limit:
                break
            yield record

    def get_game(self, game_id: str) -> dict[str, object] | None:
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT game_id, source, username, white, black, result,
                       date, end_time_utc, time_control, pgn_path, analyzed
                FROM game_index_cache
                WHERE game_id = ?
                """,
                (game_id,),
            ).fetchone()

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
                    "pgn_path": row[9],
                    "analyzed": row[10],
                }

        # Fallback to JSONL index
        for record in read_index(self.data_dir):
            if record.get("id") == game_id:
                return record
        return None

    def list_games_filtered(
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
                   date, end_time_utc, time_control, pgn_path, analyzed
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

        with self.connection as conn:
            # Get total count
            count_params = [p for p in params if not isinstance(p, int) or p < 1000]
            total_count = conn.execute(count_query, count_params).fetchone()[0]

            # Get results
            rows = conn.execute(query, params).fetchall()

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
                "pgn_path": row[9],
                "analyzed": row[10],
            }
            for row in rows
        ]

        return games, total_count

    def count_games(
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

        with self.connection as conn:
            count = conn.execute(query, params).fetchone()[0]

        return count

    def mark_game_analyzed(self, game_id: str) -> None:
        with self.connection as conn:
            conn.execute(
                """
                UPDATE game_index_cache
                SET analyzed = 1
                WHERE game_id = ?
                """,
                (game_id,),
            )

    def refresh_index_cache(self) -> int:
        with self.connection as conn:
            # Get analyzed game IDs
            rows = conn.execute("SELECT game_id FROM analysis_games").fetchall()
            analyzed_games = {row[0] for row in rows}

            count = 0
            timestamp = datetime.utcnow().isoformat()

            # Process all games with the same connection
            for record in read_index(self.data_dir):
                game_id = record.get("id")
                if not game_id:
                    continue

                analyzed = 1 if game_id in analyzed_games else 0

                # Reuse the same connection for all inserts
                conn.execute(
                    """
                    INSERT INTO game_index_cache (
                        game_id, source, username, white, black, result,
                        date, end_time_utc, time_control, pgn_path,
                        analyzed, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(game_id) DO UPDATE SET
                        analyzed = excluded.analyzed
                    """,
                    (
                        game_id,
                        record.get("source"),
                        record.get("username"),
                        record.get("white"),
                        record.get("black"),
                        record.get("result"),
                        record.get("date"),
                        record.get("end_time_utc"),
                        record.get("time_control"),
                        record.get("pgn_path"),
                        analyzed,
                        timestamp,
                    ),
                )
                count += 1

            return count

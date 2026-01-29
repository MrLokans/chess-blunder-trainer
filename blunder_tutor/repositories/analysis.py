from __future__ import annotations

from collections.abc import Iterable

from blunder_tutor.constants import CLASSIFICATION_BLUNDER
from blunder_tutor.repositories.base import BaseDbRepository


class AnalysisRepository(BaseDbRepository):
    async def analysis_exists(self, game_id: str) -> bool:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT 1 FROM analysis_games WHERE game_id = ? LIMIT 1",
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    async def write_analysis(
        self,
        *,
        game_id: str,
        pgn_path: str,
        analyzed_at: str,
        engine_path: str,
        depth: int | None,
        time_limit: float | None,
        thresholds: dict[str, int],
        moves: Iterable[dict[str, object]],
    ) -> None:
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT OR REPLACE INTO analysis_games (
                game_id, pgn_path, analyzed_at, engine_path, depth, time_limit,
                inaccuracy, mistake, blunder
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                pgn_path,
                analyzed_at,
                engine_path,
                depth,
                time_limit,
                thresholds["inaccuracy"],
                thresholds["mistake"],
                thresholds["blunder"],
            ),
        )

        await conn.execute("DELETE FROM analysis_moves WHERE game_id = ?", (game_id,))
        await conn.executemany(
            """
            INSERT INTO analysis_moves (
                game_id, ply, move_number, player, uci, san,
                eval_before, eval_after, delta, cp_loss, classification,
                best_move_uci, best_move_san, best_line, best_move_eval
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    game_id,
                    int(move["ply"]),
                    int(move["move_number"]),
                    0 if move["player"] == "white" else 1,
                    str(move["uci"]),
                    move.get("san"),
                    int(move["eval_before"]),
                    int(move["eval_after"]),
                    int(move["delta"]),
                    int(move["cp_loss"]),
                    int(move["classification"]),
                    move.get("best_move_uci"),
                    move.get("best_move_san"),
                    move.get("best_line"),
                    move.get("best_move_eval"),
                )
                for move in moves
            ],
        )
        await conn.commit()

    async def fetch_blunders(self) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT game_id, ply, player, uci, san, eval_before, eval_after, cp_loss,
                   best_move_uci, best_move_san, best_line, best_move_eval
            FROM analysis_moves
            WHERE classification = ?
            """,
            (CLASSIFICATION_BLUNDER,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "game_id": row[0],
                "ply": row[1],
                "player": row[2],
                "uci": row[3],
                "san": row[4],
                "eval_before": row[5],
                "eval_after": row[6],
                "cp_loss": row[7],
                "best_move_uci": row[8],
                "best_move_san": row[9],
                "best_line": row[10],
                "best_move_eval": row[11],
            }
            for row in rows
        ]

    async def fetch_moves(self, game_id: str) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT ply, move_number, player, uci, san, eval_before, eval_after,
                delta, cp_loss, classification
            FROM analysis_moves
            WHERE game_id = ?
            ORDER BY ply
            """,
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "ply": row[0],
                "move_number": row[1],
                "player": row[2],
                "uci": row[3],
                "san": row[4],
                "eval_before": row[5],
                "eval_after": row[6],
                "delta": row[7],
                "cp_loss": row[8],
                "classification": row[9],
            }
            for row in rows
        ]

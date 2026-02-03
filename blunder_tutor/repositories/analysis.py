from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

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
        eco_code: str | None = None,
        eco_name: str | None = None,
    ) -> None:
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT OR REPLACE INTO analysis_games (
                game_id, pgn_path, analyzed_at, engine_path, depth, time_limit,
                inaccuracy, mistake, blunder, eco_code, eco_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                eco_code,
                eco_name,
            ),
        )

        await conn.execute("DELETE FROM analysis_moves WHERE game_id = ?", (game_id,))
        await conn.executemany(
            """
            INSERT INTO analysis_moves (
                game_id, ply, move_number, player, uci, san,
                eval_before, eval_after, delta, cp_loss, classification,
                best_move_uci, best_move_san, best_line, best_move_eval, game_phase
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    move.get("game_phase"),
                )
                for move in moves
            ],
        )
        await conn.commit()

    async def fetch_blunders(
        self, game_phases: list[int] | None = None
    ) -> list[dict[str, object]]:
        conn = await self.get_connection()
        if game_phases:
            placeholders = ",".join("?" * len(game_phases))
            query = f"""
                SELECT game_id, ply, player, uci, san, eval_before, eval_after, cp_loss,
                       best_move_uci, best_move_san, best_line, best_move_eval, game_phase
                FROM analysis_moves
                WHERE classification = ? AND game_phase IN ({placeholders})
            """
            params = (CLASSIFICATION_BLUNDER, *game_phases)
        else:
            query = """
                SELECT game_id, ply, player, uci, san, eval_before, eval_after, cp_loss,
                       best_move_uci, best_move_san, best_line, best_move_eval, game_phase
                FROM analysis_moves
                WHERE classification = ?
            """
            params = (CLASSIFICATION_BLUNDER,)
        async with conn.execute(query, params) as cursor:
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
                "game_phase": row[12],
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

    async def get_game_ids_missing_phase(self) -> list[str]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT DISTINCT game_id FROM analysis_moves WHERE game_phase IS NULL
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def fetch_moves_for_phase_backfill(
        self, game_id: str
    ) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT ply, move_number
            FROM analysis_moves
            WHERE game_id = ? AND game_phase IS NULL
            ORDER BY ply
            """,
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [{"ply": row[0], "move_number": row[1]} for row in rows]

    async def update_move_phase(self, game_id: str, ply: int, game_phase: int) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "UPDATE analysis_moves SET game_phase = ? WHERE game_id = ? AND ply = ?",
            (game_phase, game_id, ply),
        )
        await conn.commit()

    async def update_moves_phases_batch(
        self, updates: list[tuple[int, str, int]]
    ) -> None:
        conn = await self.get_connection()
        await conn.executemany(
            "UPDATE analysis_moves SET game_phase = ? WHERE game_id = ? AND ply = ?",
            updates,
        )
        await conn.commit()

    async def get_game_ids_missing_eco(self) -> list[str]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT ag.game_id FROM analysis_games ag
            WHERE ag.eco_code IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM analysis_step_status ass
                WHERE ass.game_id = ag.game_id AND ass.step_id = 'eco'
            )
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def update_game_eco(
        self, game_id: str, eco_code: str | None, eco_name: str | None
    ) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "UPDATE analysis_games SET eco_code = ?, eco_name = ? WHERE game_id = ?",
            (eco_code, eco_name, game_id),
        )
        await conn.commit()

    async def get_game_eco(self, game_id: str) -> dict[str, str | None]:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT eco_code, eco_name FROM analysis_games WHERE game_id = ?",
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {"eco_code": row[0], "eco_name": row[1]}
        return {"eco_code": None, "eco_name": None}

    async def mark_step_completed(self, game_id: str, step_id: str) -> None:
        conn = await self.get_connection()
        completed_at = datetime.now(UTC).isoformat()
        await conn.execute(
            """
            INSERT OR REPLACE INTO analysis_step_status (game_id, step_id, completed_at)
            VALUES (?, ?, ?)
            """,
            (game_id, step_id, completed_at),
        )
        await conn.commit()

    async def get_completed_steps(self, game_id: str) -> set[str]:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT step_id FROM analysis_step_status WHERE game_id = ?",
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return {row[0] for row in rows}

    async def is_step_completed(self, game_id: str, step_id: str) -> bool:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT 1 FROM analysis_step_status WHERE game_id = ? AND step_id = ? LIMIT 1",
            (game_id, step_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    async def clear_step_status(self, game_id: str) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "DELETE FROM analysis_step_status WHERE game_id = ?",
            (game_id,),
        )
        await conn.commit()

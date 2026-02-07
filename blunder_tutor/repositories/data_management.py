from __future__ import annotations

from blunder_tutor.repositories.base import BaseDbRepository


class DataManagementRepository(BaseDbRepository):
    async def delete_all_data(self) -> dict[str, int]:
        async with self.write_transaction() as conn:
            counts: dict[str, int] = {}

            cursor = await conn.execute("SELECT COUNT(*) FROM puzzle_attempts")
            counts["puzzle_attempts"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM puzzle_attempts")

            cursor = await conn.execute("SELECT COUNT(*) FROM analysis_step_status")
            counts["analysis_step_status"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM analysis_step_status")

            cursor = await conn.execute("SELECT COUNT(*) FROM analysis_moves")
            counts["analysis_moves"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM analysis_moves")

            cursor = await conn.execute("SELECT COUNT(*) FROM analysis_games")
            counts["analysis_games"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM analysis_games")

            cursor = await conn.execute("SELECT COUNT(*) FROM background_jobs")
            counts["background_jobs"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM background_jobs")

            cursor = await conn.execute("SELECT COUNT(*) FROM game_index_cache")
            counts["game_index_cache"] = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM game_index_cache")

            return counts

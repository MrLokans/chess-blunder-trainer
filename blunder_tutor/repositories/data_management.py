from __future__ import annotations

import aiosqlite

from blunder_tutor.repositories.base import BaseDbRepository


async def _delete_rows(
    conn: aiosqlite.Connection, table: str, keep_job_id: str | None
) -> int:
    if table == "background_jobs" and keep_job_id:
        # The wipe job's own row must survive so its lifecycle can complete.
        cursor = await conn.execute(
            "DELETE FROM background_jobs WHERE job_id != ?", (keep_job_id,)
        )
    else:
        cursor = await conn.execute(f"DELETE FROM {table}")
    return cursor.rowcount


# (table, optional): optional tables may be missing in older DBs; their errors are
# swallowed to keep the wipe idempotent.
_WIPE_TABLES: tuple[tuple[str, bool], ...] = (
    ("srs_cards", True),
    ("trap_matches", True),
    ("puzzle_attempts", False),
    ("analysis_step_status", False),
    ("analysis_moves", False),
    ("analysis_games", False),
    ("background_jobs", False),
    ("starred_puzzles", True),
    ("game_index_cache", False),
)


class DataManagementRepository(BaseDbRepository):
    async def delete_all_data(self, keep_job_id: str | None = None) -> dict[str, int]:
        async with self.write_transaction() as conn:
            counts: dict[str, int] = {}
            for table, optional in _WIPE_TABLES:
                if optional:
                    try:
                        counts[table] = await _delete_rows(conn, table, keep_job_id)
                    except Exception:
                        counts[table] = 0
                else:
                    counts[table] = await _delete_rows(conn, table, keep_job_id)
            return counts

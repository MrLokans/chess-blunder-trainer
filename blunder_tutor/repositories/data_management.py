from __future__ import annotations

import aiosqlite

from blunder_tutor.repositories.base import BaseDbRepository


async def _count_then_delete(conn: aiosqlite.Connection, table: str) -> int:
    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
    row = await cursor.fetchone()
    count = row[0] if row else 0
    await conn.execute(f"DELETE FROM {table}")
    return count


# (table, optional). Optional tables may not exist in older databases;
# missing-table errors are swallowed to keep the wipe idempotent across
# schema versions. Order is preserved from the original implementation.
_WIPE_TABLES: tuple[tuple[str, bool], ...] = (
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
    async def delete_all_data(self) -> dict[str, int]:
        async with self.write_transaction() as conn:
            counts: dict[str, int] = {}
            for table, optional in _WIPE_TABLES:
                if optional:
                    try:
                        counts[table] = await _count_then_delete(conn, table)
                    except Exception:
                        counts[table] = 0
                else:
                    counts[table] = await _count_then_delete(conn, table)
            return counts

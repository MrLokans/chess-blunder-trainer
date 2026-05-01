from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite

from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.repositories.profile_types import (
    Profile,
    ProfileNotFoundError,
    ProfilePreferences,
    ProfileStatSnapshot,
    ProfileSyncCandidate,
)

# Per-game tables that participate in the cascade-delete path. Children are
# listed before parents so the IN-clause subqueries against game_index_cache
# continue resolving until the final delete on that table.
_GAME_CASCADE_TABLES: tuple[str, ...] = (
    "trap_matches",
    "puzzle_attempts",
    "analysis_step_status",
    "analysis_moves",
    "analysis_games",
    "starred_puzzles",
)

_PROFILE_SELECT = """
    SELECT
        p.id, p.platform, p.username, p.is_primary,
        p.created_at, p.updated_at, p.last_validated_at,
        pp.auto_sync_enabled, pp.sync_max_games
    FROM profile p
    LEFT JOIN profile_preferences pp ON pp.profile_id = p.id
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_profile(row: aiosqlite.Row) -> Profile:
    return Profile(
        id=row["id"],
        platform=row["platform"],
        username=row["username"],
        is_primary=bool(row["is_primary"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_validated_at=row["last_validated_at"],
        preferences=ProfilePreferences(
            auto_sync_enabled=bool(row["auto_sync_enabled"]),
            sync_max_games=row["sync_max_games"],
        ),
    )


def _row_to_stat(row: aiosqlite.Row) -> ProfileStatSnapshot:
    return ProfileStatSnapshot(
        mode=row["mode"],
        rating=row["rating"],
        games_count=row["games_count"],
        synced_at=row["synced_at"],
    )


async def _fetch_profile(conn: aiosqlite.Connection, profile_id: int) -> Profile | None:
    async with conn.execute(
        f"{_PROFILE_SELECT} WHERE p.id = ?", (profile_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return None if row is None else _row_to_profile(row)


async def _delete_games_for_profile(
    conn: aiosqlite.Connection, profile_id: int
) -> None:
    params = (profile_id,)
    for table in _GAME_CASCADE_TABLES:
        await conn.execute(
            f"DELETE FROM {table} WHERE game_id IN "
            f"(SELECT game_id FROM game_index_cache WHERE profile_id = ?)",
            params,
        )
    await conn.execute("DELETE FROM game_index_cache WHERE profile_id = ?", params)


async def _purge_profile_rows(conn: aiosqlite.Connection, profile_id: int) -> None:
    """Drop the profile + its 1:1 metadata rows (preferences, stats).

    Explicit because `PRAGMA foreign_keys` is not enabled on main app
    connections — the schema-level CASCADE on `profile_preferences` and
    `profile_stats` is documentation only.
    """
    params = (profile_id,)
    await conn.execute("DELETE FROM profile_stats WHERE profile_id = ?", params)
    await conn.execute("DELETE FROM profile_preferences WHERE profile_id = ?", params)
    await conn.execute("DELETE FROM profile WHERE id = ?", params)


class SqliteProfileRepository(BaseDbRepository):
    async def list_profiles(self) -> list[Profile]:
        conn = await self.get_connection()
        async with conn.execute(
            f"{_PROFILE_SELECT} ORDER BY p.platform, p.is_primary DESC, p.username"
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_profile(row) for row in rows]

    async def get(self, profile_id: int) -> Profile | None:
        conn = await self.get_connection()
        async with conn.execute(
            f"{_PROFILE_SELECT} WHERE p.id = ?", (profile_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return None if row is None else _row_to_profile(row)

    async def find_by_platform_username(
        self, platform: str, username: str
    ) -> Profile | None:
        conn = await self.get_connection()
        async with conn.execute(
            f"{_PROFILE_SELECT} WHERE p.platform = ? AND p.username = ?",
            (platform, username.lower()),
        ) as cursor:
            row = await cursor.fetchone()
        return None if row is None else _row_to_profile(row)

    async def create(
        self, platform: str, username: str, *, make_primary: bool = False
    ) -> Profile:
        normalized = username.lower()
        async with self.write_transaction() as conn:
            existing_primary = await self._has_primary_for_platform(conn, platform)
            should_be_primary = make_primary or not existing_primary
            # Demote the previous primary before inserting — the partial
            # unique index fires at INSERT time, so the new row would
            # collide otherwise.
            if should_be_primary and existing_primary:
                await conn.execute(
                    "UPDATE profile SET is_primary = 0 "
                    "WHERE platform = ? AND is_primary = 1",
                    (platform,),
                )
            now = _now_iso()
            cursor = await conn.execute(
                """
                INSERT INTO profile
                    (platform, username, is_primary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (platform, normalized, int(should_be_primary), now, now),
            )
            profile_id = cursor.lastrowid
            if profile_id is None:
                raise RuntimeError("Profile insert returned no lastrowid")
            await conn.execute(
                "INSERT INTO profile_preferences (profile_id) VALUES (?)",
                (profile_id,),
            )
        return await self._require_profile(profile_id)

    async def update(
        self,
        profile_id: int,
        *,
        username: str | None = None,
        is_primary: bool | None = None,
    ) -> Profile:
        if username is None and is_primary is None:
            return await self._require_profile(profile_id)
        async with self.write_transaction() as conn:
            current = await _fetch_profile(conn, profile_id)
            if current is None:
                raise ProfileNotFoundError(profile_id)
            new_username = (
                username.lower() if username is not None else current.username
            )
            new_is_primary = (
                is_primary if is_primary is not None else current.is_primary
            )
            # Demote any existing primary before promoting this one — the
            # partial unique index would otherwise reject the UPDATE.
            if is_primary is True:
                await conn.execute(
                    "UPDATE profile SET is_primary = 0 "
                    "WHERE platform = ? AND id != ? AND is_primary = 1",
                    (current.platform, profile_id),
                )
            await conn.execute(
                "UPDATE profile "
                "SET username = ?, is_primary = ?, updated_at = ? "
                "WHERE id = ?",
                (new_username, int(new_is_primary), _now_iso(), profile_id),
            )
        return await self._require_profile(profile_id)

    async def update_preferences(
        self,
        profile_id: int,
        *,
        auto_sync_enabled: bool | None = None,
        sync_max_games: int | None = None,
        clear_sync_max_games: bool = False,
    ) -> Profile:
        # `sync_max_games=None` (the default) means "leave unchanged".
        # Clearing the field to NULL in the DB requires the explicit
        # `clear_sync_max_games=True` flag — callers must intend it.
        if clear_sync_max_games and sync_max_games is not None:
            raise ValueError(
                "clear_sync_max_games and sync_max_games are mutually exclusive"
            )
        no_change = (
            auto_sync_enabled is None
            and sync_max_games is None
            and not clear_sync_max_games
        )
        if no_change:
            return await self._require_profile(profile_id)
        async with self.write_transaction() as conn:
            current = await _fetch_profile(conn, profile_id)
            if current is None:
                raise ProfileNotFoundError(profile_id)
            new_auto = (
                int(auto_sync_enabled)
                if auto_sync_enabled is not None
                else int(current.preferences.auto_sync_enabled)
            )
            if clear_sync_max_games:
                new_max: int | None = None
            elif sync_max_games is not None:
                new_max = sync_max_games
            else:
                new_max = current.preferences.sync_max_games
            await conn.execute(
                "UPDATE profile_preferences "
                "SET auto_sync_enabled = ?, sync_max_games = ? "
                "WHERE profile_id = ?",
                (new_auto, new_max, profile_id),
            )
        return await self._require_profile(profile_id)

    async def delete(self, profile_id: int, *, detach_games: bool) -> None:
        async with self.write_transaction() as conn:
            if await _fetch_profile(conn, profile_id) is None:
                raise ProfileNotFoundError(profile_id)
            if detach_games:
                await conn.execute(
                    "UPDATE game_index_cache SET profile_id = NULL "
                    "WHERE profile_id = ?",
                    (profile_id,),
                )
            else:
                await _delete_games_for_profile(conn, profile_id)
            await _purge_profile_rows(conn, profile_id)

    async def upsert_stats(
        self, profile_id: int, snapshots: list[ProfileStatSnapshot]
    ) -> None:
        if not snapshots:
            return
        now = _now_iso()
        async with self.write_transaction() as conn:
            if await _fetch_profile(conn, profile_id) is None:
                raise ProfileNotFoundError(profile_id)
            for snap in snapshots:
                await conn.execute(
                    """
                    INSERT INTO profile_stats
                        (profile_id, mode, rating, games_count, synced_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id, mode) DO UPDATE SET
                        rating = excluded.rating,
                        games_count = excluded.games_count,
                        synced_at = excluded.synced_at
                    """,
                    (
                        profile_id,
                        snap.mode,
                        snap.rating,
                        snap.games_count,
                        snap.synced_at or now,
                    ),
                )

    async def list_stats(self, profile_id: int) -> list[ProfileStatSnapshot]:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT mode, rating, games_count, synced_at "
            "FROM profile_stats WHERE profile_id = ? "
            "ORDER BY mode",
            (profile_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_stat(row) for row in rows]

    async def list_auto_sync_candidates(self) -> list[ProfileSyncCandidate]:
        """Return profiles eligible for auto sync, with their latest
        `profile_stats.synced_at` plus enough identity (`platform`,
        `username`) for the game-sync dispatcher to look up its own
        last-sync time in `background_jobs`. The repo just narrows by
        `auto_sync_enabled = 1` and joins in the stats timestamp; the
        scheduler does the time-based due-vs-fresh filtering.

        `LEFT JOIN` so a profile that has never synced stats still
        surfaces with `last_stats_sync_at = None` — the first-sync
        path the scheduler treats as overdue.
        """
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                p.id AS profile_id,
                p.platform AS platform,
                p.username AS username,
                MAX(ps.synced_at) AS last_stats_sync_at
            FROM profile p
            JOIN profile_preferences pp ON pp.profile_id = p.id
            LEFT JOIN profile_stats ps ON ps.profile_id = p.id
            WHERE pp.auto_sync_enabled = 1
            GROUP BY p.id
            ORDER BY p.id
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            ProfileSyncCandidate(
                profile_id=row["profile_id"],
                platform=row["platform"],
                username=row["username"],
                last_stats_sync_at=row["last_stats_sync_at"],
            )
            for row in rows
        ]

    async def touch_validated_at(self, profile_id: int) -> None:
        now = _now_iso()
        async with self.write_transaction() as conn:
            if await _fetch_profile(conn, profile_id) is None:
                raise ProfileNotFoundError(profile_id)
            await conn.execute(
                "UPDATE profile SET last_validated_at = ?, updated_at = ? WHERE id = ?",
                (now, now, profile_id),
            )

    async def _has_primary_for_platform(
        self, conn: aiosqlite.Connection, platform: str
    ) -> bool:
        async with conn.execute(
            "SELECT 1 FROM profile WHERE platform = ? AND is_primary = 1 LIMIT 1",
            (platform,),
        ) as cursor:
            return await cursor.fetchone() is not None

    async def _require_profile(self, profile_id: int) -> Profile:
        result = await self.get(profile_id)
        if result is None:
            raise ProfileNotFoundError(profile_id)
        return result

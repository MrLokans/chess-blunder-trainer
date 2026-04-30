from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import closing
from pathlib import Path

import pytest

from blunder_tutor.repositories.profile import (
    ProfileNotFoundError,
    ProfileStatSnapshot,
    SqliteProfileRepository,
)


@pytest.fixture
async def repo(db_path: Path) -> AsyncGenerator[SqliteProfileRepository]:
    repository = SqliteProfileRepository(db_path)
    yield repository
    await repository.close()


def _insert_game(db: Path, *, game_id: str, profile_id: int | None) -> None:
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, pgn_content, indexed_at, profile_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (game_id, "lichess", "alice", "1.e4 e5", "2026-04-30", profile_id),
        )
        conn.commit()


_GAME_CASCADE_INSERTS: tuple[tuple[str, str], ...] = (
    (
        "analysis_games",
        "INSERT INTO analysis_games "
        "(game_id, pgn_path, analyzed_at, engine_path, "
        " inaccuracy, mistake, blunder) "
        "VALUES (?, '/tmp/p.pgn', '2026-04-30', '/sf', 0, 0, 0)",
    ),
    (
        "analysis_moves",
        "INSERT INTO analysis_moves "
        "(game_id, ply, move_number, player, uci, "
        " eval_before, eval_after, delta, cp_loss, classification) "
        "VALUES (?, 1, 1, 0, 'e2e4', 0, 0, 0, 0, 0)",
    ),
    (
        "analysis_step_status",
        "INSERT INTO analysis_step_status (game_id, step_id, completed_at) "
        "VALUES (?, 'step1', '2026-04-30')",
    ),
    (
        "puzzle_attempts",
        "INSERT INTO puzzle_attempts "
        "(game_id, ply, username, was_correct, attempted_at) "
        "VALUES (?, 1, 'alice', 0, '2026-04-30')",
    ),
    (
        "trap_matches",
        "INSERT INTO trap_matches "
        "(game_id, trap_id, match_type, victim_side, "
        " user_was_victim, mistake_ply) "
        "VALUES (?, 'london', 'entered', 'white', 0, NULL)",
    ),
    (
        "starred_puzzles",
        "INSERT INTO starred_puzzles (game_id, ply, starred_at) "
        "VALUES (?, 1, '2026-04-30')",
    ),
)


def _populate_game_cascade(db: Path, game_id: str) -> None:
    with closing(sqlite3.connect(str(db))) as conn:
        for _table, sql in _GAME_CASCADE_INSERTS:
            conn.execute(sql, (game_id,))
        conn.commit()


class TestCreate:
    async def test_first_profile_is_auto_primary(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        assert profile.is_primary is True
        assert profile.username == "alice"
        assert profile.preferences.auto_sync_enabled is True
        assert profile.preferences.sync_max_games is None

    async def test_second_profile_same_platform_is_not_primary(
        self, repo: SqliteProfileRepository
    ) -> None:
        await repo.create("lichess", "alice")
        second = await repo.create("lichess", "bob")
        assert second.is_primary is False

    async def test_make_primary_demotes_existing_primary(
        self, repo: SqliteProfileRepository
    ) -> None:
        first = await repo.create("lichess", "alice")
        second = await repo.create("lichess", "bob", make_primary=True)
        assert second.is_primary is True
        first_after = await repo.get(first.id)
        assert first_after is not None
        assert first_after.is_primary is False

    async def test_lowercases_username(self, repo: SqliteProfileRepository) -> None:
        profile = await repo.create("lichess", "AliceCarlsen")
        assert profile.username == "alicecarlsen"

    async def test_independent_platforms_each_get_their_own_primary(
        self, repo: SqliteProfileRepository
    ) -> None:
        lichess = await repo.create("lichess", "alice")
        chesscom = await repo.create("chesscom", "alice")
        assert lichess.is_primary is True
        assert chesscom.is_primary is True


class TestGet:
    async def test_returns_none_for_unknown_id(
        self, repo: SqliteProfileRepository
    ) -> None:
        assert await repo.get(999) is None

    async def test_returns_profile_with_default_preferences(
        self, repo: SqliteProfileRepository
    ) -> None:
        created = await repo.create("lichess", "alice")
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.preferences.auto_sync_enabled is True
        assert fetched.preferences.sync_max_games is None


class TestFindByPlatformUsername:
    async def test_finds_normalized_username(
        self, repo: SqliteProfileRepository
    ) -> None:
        await repo.create("lichess", "alice")
        found = await repo.find_by_platform_username("lichess", "ALICE")
        assert found is not None
        assert found.username == "alice"

    async def test_returns_none_when_no_match(
        self, repo: SqliteProfileRepository
    ) -> None:
        await repo.create("lichess", "alice")
        assert await repo.find_by_platform_username("lichess", "bob") is None
        assert await repo.find_by_platform_username("chesscom", "alice") is None


class TestListProfiles:
    async def test_empty(self, repo: SqliteProfileRepository) -> None:
        assert not await repo.list_profiles()

    async def test_orders_by_platform_then_primary_first(
        self, repo: SqliteProfileRepository
    ) -> None:
        await repo.create("lichess", "alice")
        await repo.create("lichess", "bob")
        await repo.create("chesscom", "carla")
        profiles = await repo.list_profiles()
        platforms = [p.platform for p in profiles]
        assert platforms == ["chesscom", "lichess", "lichess"]
        # Within lichess, the primary (alice) sorts before non-primary (bob).
        lichess_profiles = [p for p in profiles if p.platform == "lichess"]
        assert lichess_profiles[0].is_primary is True
        assert lichess_profiles[1].is_primary is False


class TestUpdate:
    async def test_username_change_lowercases(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        updated = await repo.update(profile.id, username="ALICEcarlsen")
        assert updated.username == "alicecarlsen"

    async def test_setting_is_primary_demotes_existing(
        self, repo: SqliteProfileRepository
    ) -> None:
        first = await repo.create("lichess", "alice")
        second = await repo.create("lichess", "bob")
        updated = await repo.update(second.id, is_primary=True)
        assert updated.is_primary is True
        first_after = await repo.get(first.id)
        assert first_after is not None
        assert first_after.is_primary is False

    async def test_unknown_id_raises(self, repo: SqliteProfileRepository) -> None:
        with pytest.raises(ProfileNotFoundError):
            await repo.update(999, username="anyone")

    async def test_no_op_when_no_fields_provided(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        result = await repo.update(profile.id)
        assert result.username == profile.username
        assert result.is_primary == profile.is_primary


class TestUpdatePreferences:
    async def test_auto_sync_enabled_only(self, repo: SqliteProfileRepository) -> None:
        profile = await repo.create("lichess", "alice")
        result = await repo.update_preferences(profile.id, auto_sync_enabled=False)
        assert result.preferences.auto_sync_enabled is False
        assert result.preferences.sync_max_games is None

    async def test_sync_max_games_only(self, repo: SqliteProfileRepository) -> None:
        profile = await repo.create("lichess", "alice")
        await repo.update_preferences(profile.id, auto_sync_enabled=False)
        result = await repo.update_preferences(profile.id, sync_max_games=50)
        assert result.preferences.auto_sync_enabled is False
        assert result.preferences.sync_max_games == 50

    async def test_unknown_id_raises(self, repo: SqliteProfileRepository) -> None:
        with pytest.raises(ProfileNotFoundError):
            await repo.update_preferences(999, auto_sync_enabled=False)

    async def test_clear_sync_max_games_sets_null(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        await repo.update_preferences(profile.id, sync_max_games=50)
        result = await repo.update_preferences(profile.id, clear_sync_max_games=True)
        assert result.preferences.sync_max_games is None

    async def test_clear_conflicts_with_value_raises(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        with pytest.raises(ValueError):
            await repo.update_preferences(
                profile.id, sync_max_games=50, clear_sync_max_games=True
            )


class TestDelete:
    async def test_detach_keeps_games_with_null_profile_id(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
    ) -> None:
        profile = await repo.create("lichess", "alice")
        _insert_game(db_path, game_id="g1", profile_id=profile.id)

        await repo.delete(profile.id, detach_games=True)

        with closing(sqlite3.connect(str(db_path))) as conn:
            row = conn.execute(
                "SELECT profile_id FROM game_index_cache WHERE game_id = 'g1'"
            ).fetchone()
        assert row is not None
        assert row[0] is None

    async def test_cascade_removes_games(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
    ) -> None:
        profile = await repo.create("lichess", "alice")
        _insert_game(db_path, game_id="g_owned", profile_id=profile.id)
        _insert_game(db_path, game_id="g_unrelated", profile_id=None)

        await repo.delete(profile.id, detach_games=False)

        with closing(sqlite3.connect(str(db_path))) as conn:
            owned = conn.execute(
                "SELECT 1 FROM game_index_cache WHERE game_id = 'g_owned'"
            ).fetchone()
            unrelated = conn.execute(
                "SELECT 1 FROM game_index_cache WHERE game_id = 'g_unrelated'"
            ).fetchone()
        assert owned is None
        assert unrelated is not None

    async def test_unknown_id_raises(self, repo: SqliteProfileRepository) -> None:
        with pytest.raises(ProfileNotFoundError):
            await repo.delete(999, detach_games=True)

    async def test_cascade_walks_all_per_game_tables(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
    ) -> None:
        profile = await repo.create("lichess", "alice")
        _insert_game(db_path, game_id="g1", profile_id=profile.id)
        _populate_game_cascade(db_path, "g1")

        await repo.delete(profile.id, detach_games=False)

        with closing(sqlite3.connect(str(db_path))) as conn:
            for table, _sql in _GAME_CASCADE_INSERTS:
                row = conn.execute(
                    f"SELECT 1 FROM {table} WHERE game_id = ?", ("g1",)
                ).fetchone()
                assert row is None, f"{table} retained rows for deleted game"

    async def test_removes_preferences_and_stats(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
    ) -> None:
        profile = await repo.create("lichess", "alice")
        await repo.upsert_stats(
            profile.id,
            [ProfileStatSnapshot(mode="bullet", rating=1500, games_count=100)],
        )

        await repo.delete(profile.id, detach_games=True)

        with closing(sqlite3.connect(str(db_path))) as conn:
            prefs = conn.execute(
                "SELECT 1 FROM profile_preferences WHERE profile_id = ?",
                (profile.id,),
            ).fetchone()
            stats = conn.execute(
                "SELECT 1 FROM profile_stats WHERE profile_id = ?",
                (profile.id,),
            ).fetchone()
            row = conn.execute(
                "SELECT 1 FROM profile WHERE id = ?", (profile.id,)
            ).fetchone()
        assert prefs is None
        assert stats is None
        assert row is None


class TestStatsUpsert:
    async def test_inserts_then_overwrites_keyed_by_mode(
        self, repo: SqliteProfileRepository
    ) -> None:
        profile = await repo.create("lichess", "alice")
        await repo.upsert_stats(
            profile.id,
            [
                ProfileStatSnapshot(mode="bullet", rating=1500, games_count=100),
                ProfileStatSnapshot(mode="blitz", rating=1700, games_count=200),
            ],
        )
        first = {
            s.mode: (s.rating, s.games_count) for s in await repo.list_stats(profile.id)
        }
        assert first == {"bullet": (1500, 100), "blitz": (1700, 200)}

        await repo.upsert_stats(
            profile.id,
            [
                ProfileStatSnapshot(mode="bullet", rating=1550, games_count=110),
                ProfileStatSnapshot(mode="classical", rating=1800, games_count=50),
            ],
        )
        second_stats = await repo.list_stats(profile.id)
        second = {s.mode: (s.rating, s.games_count) for s in second_stats}
        assert second == {
            "bullet": (1550, 110),
            "blitz": (1700, 200),
            "classical": (1800, 50),
        }
        assert len(second_stats) == 3

    async def test_empty_snapshots_is_noop(self, repo: SqliteProfileRepository) -> None:
        profile = await repo.create("lichess", "alice")
        await repo.upsert_stats(profile.id, [])
        assert not await repo.list_stats(profile.id)

    async def test_unknown_id_raises(self, repo: SqliteProfileRepository) -> None:
        with pytest.raises(ProfileNotFoundError):
            await repo.upsert_stats(
                999,
                [ProfileStatSnapshot(mode="bullet", rating=1500, games_count=10)],
            )


class TestTouchValidatedAt:
    async def test_sets_timestamp(self, repo: SqliteProfileRepository) -> None:
        profile = await repo.create("lichess", "alice")
        assert profile.last_validated_at is None
        await repo.touch_validated_at(profile.id)
        after = await repo.get(profile.id)
        assert after is not None
        assert after.last_validated_at is not None

    async def test_unknown_id_raises(self, repo: SqliteProfileRepository) -> None:
        with pytest.raises(ProfileNotFoundError):
            await repo.touch_validated_at(999)

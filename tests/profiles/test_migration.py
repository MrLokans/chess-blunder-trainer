from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
MIGRATION_008 = REPO_ROOT / "alembic" / "versions" / "008_tracked_profiles.py"


def _migrate(db_path: Path, target: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, target)


def _load_migration_008() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_migration_008", MIGRATION_008)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _table_columns(db_path: Path, table: str) -> set[str]:
    with closing(sqlite3.connect(str(db_path))) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _index_names(db_path: Path, table: str) -> set[str]:
    with closing(sqlite3.connect(str(db_path))) as conn:
        rows = conn.execute(f"PRAGMA index_list({table})").fetchall()
    return {row[1] for row in rows}


def _stage_db_at_007(
    tmp_path: Path,
    *,
    lichess_username: str | None = None,
    chesscom_username: str | None = None,
) -> Path:
    db = tmp_path / "test.sqlite"
    _migrate(db, "007")
    with closing(sqlite3.connect(str(db))) as conn:
        if lichess_username is not None:
            conn.execute(
                "UPDATE app_settings SET value = ? WHERE key = 'lichess_username'",
                (lichess_username,),
            )
        if chesscom_username is not None:
            conn.execute(
                "UPDATE app_settings SET value = ? WHERE key = 'chesscom_username'",
                (chesscom_username,),
            )
        conn.commit()
    return db


def _insert_game(db: Path, *, game_id: str, source: str, username: str) -> None:
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, pgn_content, indexed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (game_id, source, username, "1.e4 e5", "2026-04-30"),
        )
        conn.commit()


def _list_profiles(db: Path) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(str(db))) as conn:
        return conn.execute(
            "SELECT platform, username, is_primary FROM profile "
            "ORDER BY platform, username"
        ).fetchall()


def _game_profile_id(db: Path, game_id: str) -> int | None:
    with closing(sqlite3.connect(str(db))) as conn:
        row = conn.execute(
            "SELECT profile_id FROM game_index_cache WHERE game_id = ?",
            (game_id,),
        ).fetchone()
    return None if row is None else row[0]


class TestSchemaMigration:
    def test_creates_profile_table(self, db_path: Path) -> None:
        cols = _table_columns(db_path, "profile")
        assert {
            "id",
            "platform",
            "username",
            "is_primary",
            "created_at",
            "updated_at",
            "last_validated_at",
        }.issubset(cols)

    def test_creates_profile_preferences_table(self, db_path: Path) -> None:
        cols = _table_columns(db_path, "profile_preferences")
        assert {"profile_id", "auto_sync_enabled", "sync_max_games"}.issubset(cols)

    def test_creates_profile_stats_table(self, db_path: Path) -> None:
        cols = _table_columns(db_path, "profile_stats")
        assert {
            "profile_id",
            "mode",
            "rating",
            "games_count",
            "synced_at",
        }.issubset(cols)

    def test_adds_profile_id_column_to_game_index_cache(self, db_path: Path) -> None:
        cols = _table_columns(db_path, "game_index_cache")
        assert "profile_id" in cols

    def test_creates_partial_primary_index(self, db_path: Path) -> None:
        assert "idx_profile_one_primary_per_platform" in _index_names(
            db_path, "profile"
        )

    def test_creates_game_index_cache_profile_id_index(self, db_path: Path) -> None:
        assert "idx_game_index_cache_profile_id" in _index_names(
            db_path, "game_index_cache"
        )


class TestPartialUniqueIndex:
    def test_blocks_two_primaries_on_same_platform(self, db_path: Path) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) VALUES (?, ?, 1)",
                ("lichess", "alice"),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO profile (platform, username, is_primary) "
                    "VALUES (?, ?, 1)",
                    ("lichess", "bob"),
                )

    def test_allows_non_primary_alongside_primary(self, db_path: Path) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) VALUES (?, ?, 1)",
                ("lichess", "alice"),
            )
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) VALUES (?, ?, 0)",
                ("lichess", "bob"),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM profile WHERE platform = ?",
                ("lichess",),
            ).fetchone()[0]
            assert count == 2

    def test_allows_one_primary_per_distinct_platform(self, db_path: Path) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) VALUES (?, ?, 1)",
                ("lichess", "alice"),
            )
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) VALUES (?, ?, 1)",
                ("chesscom", "alice"),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM profile WHERE is_primary = 1"
            ).fetchone()[0]
            assert count == 2


class TestDataStepBackfill:
    def test_with_both_usernames_creates_two_primary_profiles(
        self, tmp_path: Path
    ) -> None:
        db = _stage_db_at_007(
            tmp_path, lichess_username="alice", chesscom_username="bob"
        )
        _insert_game(db, game_id="g_lichess", source="lichess", username="alice")
        _insert_game(db, game_id="g_chesscom", source="chesscom", username="bob")
        _migrate(db, "head")

        assert _list_profiles(db) == [
            ("chesscom", "bob", 1),
            ("lichess", "alice", 1),
        ]
        assert _game_profile_id(db, "g_lichess") is not None
        assert _game_profile_id(db, "g_chesscom") is not None

    def test_with_only_lichess_creates_one_profile(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(tmp_path, lichess_username="alice")
        _insert_game(db, game_id="g_lichess", source="lichess", username="alice")
        _insert_game(db, game_id="g_chesscom", source="chesscom", username="bob")
        _migrate(db, "head")

        assert _list_profiles(db) == [("lichess", "alice", 1)]
        assert _game_profile_id(db, "g_lichess") is not None
        assert _game_profile_id(db, "g_chesscom") is None

    def test_with_neither_creates_no_profiles(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(tmp_path)
        _insert_game(db, game_id="g_lichess", source="lichess", username="alice")
        _migrate(db, "head")

        assert _list_profiles(db) == []
        assert _game_profile_id(db, "g_lichess") is None

    def test_creates_default_preferences_row_per_profile(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(tmp_path, lichess_username="alice")
        _migrate(db, "head")

        with closing(sqlite3.connect(str(db))) as conn:
            prefs = conn.execute(
                "SELECT auto_sync_enabled, sync_max_games "
                "FROM profile_preferences "
                "JOIN profile ON profile.id = profile_preferences.profile_id "
                "WHERE profile.username = 'alice'"
            ).fetchone()
        assert prefs == (1, None)

    def test_orphan_games_remain_untagged(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(tmp_path, lichess_username="alice")
        _insert_game(db, game_id="g_orphan", source="lichess", username="oldname")
        _migrate(db, "head")

        assert _game_profile_id(db, "g_orphan") is None

    def test_normalizes_username_case_and_tags_games(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(tmp_path, lichess_username="Alice")
        _insert_game(db, game_id="g_alice", source="lichess", username="alice")
        _migrate(db, "head")

        assert _list_profiles(db) == [("lichess", "alice", 1)]
        assert _game_profile_id(db, "g_alice") is not None

    def test_idempotent_when_data_step_replayed(self, tmp_path: Path) -> None:
        db = _stage_db_at_007(
            tmp_path, lichess_username="alice", chesscom_username="bob"
        )
        _insert_game(db, game_id="g1", source="lichess", username="alice")
        _migrate(db, "head")

        before = _list_profiles(db)
        before_game = _game_profile_id(db, "g1")

        migration = _load_migration_008()
        engine = sa.create_engine(f"sqlite:///{db}")
        with engine.begin() as conn:
            migration._apply_legacy_backfill(conn)
        engine.dispose()

        assert _list_profiles(db) == before
        assert _game_profile_id(db, "g1") == before_game


class TestOnDeleteSetNullForGames:
    def test_deleting_profile_nulls_game_profile_id(self, db_path: Path) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO profile (platform, username, is_primary) "
                "VALUES ('lichess', 'alice', 1)"
            )
            profile_id = conn.execute(
                "SELECT id FROM profile WHERE username = 'alice'"
            ).fetchone()[0]

            conn.execute(
                "INSERT INTO game_index_cache "
                "(game_id, source, username, pgn_content, indexed_at, profile_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("g1", "lichess", "alice", "1.e4 e5", "2026-04-30", profile_id),
            )
            conn.commit()

            conn.execute("DELETE FROM profile WHERE id = ?", (profile_id,))
            conn.commit()

            row = conn.execute(
                "SELECT profile_id FROM game_index_cache WHERE game_id = 'g1'"
            ).fetchone()
            assert row is not None
            assert row[0] is None

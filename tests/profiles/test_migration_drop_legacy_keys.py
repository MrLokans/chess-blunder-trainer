"""Tests for the legacy username-key drop (alembic 010)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


def _migrate(db_path: Path, target: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, target)


def _legacy_key_count(db_path: Path) -> int:
    with closing(sqlite3.connect(str(db_path))) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM app_settings "
            "WHERE key IN ('lichess_username', 'chesscom_username')"
        ).fetchone()
    return row[0]


def _profile_rows(db_path: Path) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(str(db_path))) as conn:
        return conn.execute(
            "SELECT platform, username, is_primary FROM profile "
            "ORDER BY platform, username"
        ).fetchall()


def _stage_at_009(
    tmp_path: Path,
    *,
    lichess: str | None = None,
    chesscom: str | None = None,
) -> Path:
    """Build a DB at revision 009 — the moment just before the drop —
    with whatever legacy username values the test wants to inject.
    """
    db = tmp_path / "test.sqlite"
    _migrate(db, "009")
    # Migration 008 inserts profile rows from non-empty legacy keys; for
    # tests we want full control, so we wipe and reinsert here.
    with closing(sqlite3.connect(str(db))) as conn:
        if lichess is not None:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES "
                "('lichess_username', ?)",
                (lichess,),
            )
        if chesscom is not None:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES "
                "('chesscom_username', ?)",
                (chesscom,),
            )
        conn.commit()
    return db


class TestUpgrade:
    def test_drops_both_legacy_keys(self, tmp_path: Path) -> None:
        db = _stage_at_009(tmp_path, lichess="alice", chesscom="bob")
        assert _legacy_key_count(db) == 2
        _migrate(db, "010")
        assert _legacy_key_count(db) == 0

    def test_idempotent_on_repeated_upgrade(self, tmp_path: Path) -> None:
        # Re-running through the same revision after a manual rollback
        # of just the data step should still be a no-op against the DELETE.
        db = _stage_at_009(tmp_path, lichess="alice")
        _migrate(db, "010")
        # Manually re-run upgrade SQL; alembic itself skips already-applied
        # revisions, so we exercise the SQL directly.
        with closing(sqlite3.connect(str(db))) as conn:
            conn.execute(
                "DELETE FROM app_settings "
                "WHERE key IN ('lichess_username', 'chesscom_username')"
            )
            conn.commit()
        assert _legacy_key_count(db) == 0

    def test_handles_missing_keys(self, tmp_path: Path) -> None:
        # Defensive: a DB that was hand-pruned before this migration
        # should not error.
        db = tmp_path / "test.sqlite"
        _migrate(db, "009")
        with closing(sqlite3.connect(str(db))) as conn:
            conn.execute(
                "DELETE FROM app_settings "
                "WHERE key IN ('lichess_username', 'chesscom_username')"
            )
            conn.commit()
        _migrate(db, "010")
        assert _legacy_key_count(db) == 0

    def test_preserves_profile_rows_and_links(self, tmp_path: Path) -> None:
        # The drop should only touch app_settings — profile rows backfilled
        # by migration 008 must survive intact, and game_index_cache.profile_id
        # links must remain.
        db = _stage_at_009(tmp_path, lichess="alice")
        # Force migration 008's backfill by re-running its data step against
        # the freshly injected legacy key. Since 008 already ran during the
        # upgrade chain, we manually mirror its behavior here.
        with closing(sqlite3.connect(str(db))) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO profile (platform, username, is_primary) "
                "VALUES ('lichess', 'alice', 1)"
            )
            profile_id = conn.execute(
                "SELECT id FROM profile WHERE platform = 'lichess' "
                "AND username = 'alice'"
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO profile_preferences (profile_id) VALUES (?)",
                (profile_id,),
            )
            conn.execute(
                "INSERT INTO game_index_cache "
                "(game_id, source, username, pgn_content, indexed_at, profile_id) "
                "VALUES ('g1', 'lichess', 'alice', '1.e4', '2026-04-30', ?)",
                (profile_id,),
            )
            conn.commit()

        _migrate(db, "010")

        assert _profile_rows(db) == [("lichess", "alice", 1)]
        with closing(sqlite3.connect(str(db))) as conn:
            row = conn.execute(
                "SELECT profile_id FROM game_index_cache WHERE game_id = 'g1'"
            ).fetchone()
        assert row[0] is not None


class TestDowngrade:
    def test_restores_empty_keys(self, tmp_path: Path) -> None:
        db = _stage_at_009(tmp_path, lichess="alice", chesscom="bob")
        _migrate(db, "010")
        assert _legacy_key_count(db) == 0
        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
        command.downgrade(cfg, "009")
        # Both keys are present again; values are NULL because the original
        # population was lazy on first use.
        with closing(sqlite3.connect(str(db))) as conn:
            rows = conn.execute(
                "SELECT key, value FROM app_settings "
                "WHERE key IN ('lichess_username', 'chesscom_username') "
                "ORDER BY key"
            ).fetchall()
        assert rows == [("chesscom_username", None), ("lichess_username", None)]

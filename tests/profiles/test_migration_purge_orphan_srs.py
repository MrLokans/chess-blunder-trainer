from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _migrate(db_path: Path, target: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, target)


def test_upgrade_deletes_only_orphan_cards(tmp_path: Path):
    db = tmp_path / "test.sqlite"
    _migrate(db, "011")
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, pgn_content, indexed_at) "
            "VALUES ('kept', 'lichess', 'alice', '', '2026-01-01')"
        )
        for game_id in ("kept", "orphan"):
            conn.execute(
                "INSERT INTO srs_cards (game_id, ply, due_at, enrolled_at) "
                "VALUES (?, 1, '2026-01-01', '2026-01-01')",
                (game_id,),
            )
        conn.commit()

    _migrate(db, "012")

    with closing(sqlite3.connect(str(db))) as conn:
        remaining = [row[0] for row in conn.execute("SELECT game_id FROM srs_cards")]
    assert remaining == ["kept"]

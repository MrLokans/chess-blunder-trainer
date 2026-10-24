from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from blunder_tutor.analysis.tactics import TacticalPattern
from tests.helpers.blunder_corpus import DEMO_DB

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
# c6 blocks a check like the best move b5 does; both pin a pawn (GH #17 pattern).
FORCED_PIN = (
    "529301a1e700ffbdbdcbb846944ff5a4a9f4ca439c09274d1d52305c3e0da08a",
    40,
)
BROKEN_GAME = "82c510c40d00a317f3c2a9b58323a2fadcb9d65715b58684084fc2d0df6f6fc7"

_TAGS_SQL = (
    "SELECT game_id, ply, tactical_pattern, tactical_reason FROM analysis_moves "
    "WHERE classification = 3 ORDER BY game_id, ply"
)


def _migrate(db_path: Path, target: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, target)


def _tags(db_path: Path) -> dict[tuple[str, int], tuple[int | None, str | None]]:
    with closing(sqlite3.connect(str(db_path))) as conn:
        return {
            (game_id, ply): (pattern, reason)
            for game_id, ply, pattern, reason in conn.execute(_TAGS_SQL)
        }


@pytest.fixture
def demo_at_012(tmp_path: Path) -> Path:
    if not DEMO_DB.exists():
        pytest.skip("demo DB not available")
    db = tmp_path / "demo.sqlite3"
    shutil.copy(DEMO_DB, db)
    _migrate(db, "012")
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "UPDATE game_index_cache SET pgn_content = '' WHERE game_id = ?",
            (BROKEN_GAME,),
        )
        conn.commit()
    return db


def test_upgrade_reclassifies_tags_in_place(demo_at_012: Path):
    before = _tags(demo_at_012)

    _migrate(demo_at_012, "013")

    after = _tags(demo_at_012)
    assert before[FORCED_PIN][0] == TacticalPattern.PIN
    assert after[FORCED_PIN][0] != TacticalPattern.PIN
    assert all(pattern is not None for pattern, _ in after.values())
    broken = [key for key in before if key[0] == BROKEN_GAME]
    assert broken
    assert all(after[key] == before[key] for key in broken)

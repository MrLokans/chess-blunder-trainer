from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _config(db_path: Path) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _settings(db_path: Path) -> dict[str, str]:
    with closing(sqlite3.connect(str(db_path))) as conn:
        return dict(
            conn.execute("SELECT key, value FROM app_settings WHERE key LIKE 'theme_%'")
        )


def _store(db_path: Path, rows: list[tuple[str, str]]) -> None:
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", rows
        )
        conn.commit()


def test_rewrites_the_old_green_defaults_and_back(tmp_path: Path):
    db = tmp_path / "main.sqlite3"
    cfg = _config(db)
    command.upgrade(cfg, "014")
    _store(
        db,
        [
            ("theme_heatmap_l1", "#b8d9ca"),
            ("theme_heatmap_l4", "#1A6B2A"),
            ("theme_heatmap_empty", "#E8E4DB"),
        ],
    )

    command.upgrade(cfg, "015")
    after = _settings(db)
    assert after["theme_heatmap_l1"] == "#BFB9AC"
    assert after["theme_heatmap_l4"] == "#1A1A1A"
    assert after["theme_heatmap_empty"] == "#E8E4DB"

    command.downgrade(cfg, "014")
    assert _settings(db)["theme_heatmap_l1"] == "#B8D9CA"


def test_keeps_a_custom_heatmap_colour(tmp_path: Path):
    db = tmp_path / "main.sqlite3"
    cfg = _config(db)
    command.upgrade(cfg, "014")
    _store(db, [("theme_heatmap_l2", "#40C463")])

    command.upgrade(cfg, "015")
    assert _settings(db)["theme_heatmap_l2"] == "#40C463"

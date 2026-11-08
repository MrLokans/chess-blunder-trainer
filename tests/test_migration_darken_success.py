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


def test_rewrites_only_the_old_default_success(tmp_path: Path):
    db = tmp_path / "main.sqlite3"
    cfg = _config(db)
    command.upgrade(cfg, "013")
    with closing(sqlite3.connect(str(db))) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            [("theme_success", "#2d8f3e"), ("theme_heatmap_l3", "#2D8F3E")],
        )
        conn.commit()

    command.upgrade(cfg, "014")
    after = _settings(db)
    assert after["theme_success"] == "#247A33"
    assert after["theme_heatmap_l3"] == "#2D8F3E"

    command.downgrade(cfg, "013")
    assert _settings(db)["theme_success"] == "#2D8F3E"


def test_keeps_a_custom_success_colour(tmp_path: Path):
    db = tmp_path / "main.sqlite3"
    cfg = _config(db)
    command.upgrade(cfg, "013")
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('theme_success', '#40916C')"
        )
        conn.commit()

    command.upgrade(cfg, "014")
    assert _settings(db)["theme_success"] == "#40916C"

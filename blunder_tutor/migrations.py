from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command
from blunder_tutor.secure_fs import restrict_umask, secure_db_file

logger = logging.getLogger(__name__)

INITIAL_REVISION = "001"


def get_alembic_config(db_path: Path) -> Config:
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    config = Config(str(alembic_ini))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    return config


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _has_alembic_version(conn: sqlite3.Connection) -> bool:
    return _table_exists(conn, "alembic_version")


def _has_existing_schema(conn: sqlite3.Connection) -> bool:
    return _table_exists(conn, "game_index_cache")


def run_migrations(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    config = get_alembic_config(db_path)

    # Wrap in a tight umask: alembic creates the DB file, which would sit at 0644 until
    # `secure_db_file` chmods it.
    with restrict_umask():
        if db_path.exists():
            with closing(sqlite3.connect(str(db_path))) as conn:
                has_alembic = _has_alembic_version(conn)
                has_schema = _has_existing_schema(conn)

                if not has_alembic and has_schema:
                    logger.info(
                        "Stamping existing database with revision %s",
                        INITIAL_REVISION,
                    )
                    command.stamp(config, INITIAL_REVISION)

        command.upgrade(config, "head")

    # Belt: also covers existing DBs that predate the lock-down.
    secure_db_file(db_path)


def main() -> None:
    db_path_env = os.environ.get("DB_PATH") or os.environ.get("BLUNDER_TUTOR_DB_PATH")
    db_path = Path(db_path_env) if db_path_env else Path("data/main.sqlite3")

    print(f"Running migrations on {db_path}")  # noqa: WPS421 — CLI entry point output.
    run_migrations(db_path)
    print("Migrations complete")  # noqa: WPS421 — CLI entry point output.


if __name__ == "__main__":
    main()

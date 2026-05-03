from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    # `disable_existing_loggers=False` keeps every already-configured
    # application logger (e.g. `blunder_tutor.web.app`) attached to
    # its handlers. The default is True, which disables every logger
    # not named in alembic.ini — a silent footgun for tests that run
    # migrations and then assert on application log output.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def get_database_url() -> str:
    db_path = os.environ.get("BLUNDER_TUTOR_DB_PATH")
    if db_path:
        return f"sqlite:///{db_path}"

    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url

    default_path = Path("data/main.sqlite3")
    return f"sqlite:///{default_path}"


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_database_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    # `dispose()` is required because the test suite calls `run_migrations()`
    # many times per session (one fresh DB per test); without it, SQLAlchemy
    # keeps the underlying sqlite3 connections alive long enough for GC to
    # fire `Connection.__del__` after the test completes, surfacing as a
    # ResourceWarning that the strict pytest filter escalates to an error.
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=None,
                render_as_batch=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

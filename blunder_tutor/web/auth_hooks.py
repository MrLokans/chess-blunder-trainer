from __future__ import annotations

import shutil
from pathlib import Path

from blunder_tutor.auth.types import User, UserId
from blunder_tutor.migrations import run_migrations
from blunder_tutor.secure_fs import secure_user_dir


def resolve_user_db_path(users_dir: Path, user_id: UserId) -> Path:
    """blunder_tutor's per-user DB layout. AuthService receives this as
    an injected ``db_path_resolver`` so the auth core never knows about
    filesystem topology — a SaaS pivot to a shared DB swaps this for a
    tenant-id resolver and nothing in ``blunder_tutor/auth/`` changes.
    """
    return users_dir / user_id / "main.sqlite3"


async def materialize_user_dir(users_dir: Path, user: User) -> None:
    """``on_after_register`` hook for credentials-mode signup: tighten
    permissions on the per-user data dir and run the project's schema
    migrations against the fresh per-user SQLite file. Sync work runs
    inside an async function because ``run_migrations`` is sync and
    idempotent — moving it onto a thread pool would gain nothing while
    the registration request is already serialized behind the auth
    write lock.
    """
    user_db_path = resolve_user_db_path(users_dir, user.id)
    secure_user_dir(user_db_path.parent)
    run_migrations(user_db_path)


async def cleanup_user_dir(users_dir: Path, user_id: UserId) -> None:
    """``on_after_delete`` hook: drop the per-user data dir after the
    auth tables have committed the user-row removal. Missing dir is a
    silent no-op — the user could have been an OAuth-only identity
    that never had data materialized, or a previous delete already
    cleaned the filesystem.
    """
    user_dir = users_dir / user_id
    if user_dir.exists():
        shutil.rmtree(user_dir)

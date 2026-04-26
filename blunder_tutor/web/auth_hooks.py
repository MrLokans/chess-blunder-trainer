from __future__ import annotations

import logging
import shutil
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from pathlib import Path

from blunder_tutor import secure_fs
from blunder_tutor.auth import User, UserId
from blunder_tutor.migrations import run_migrations
from blunder_tutor.secure_fs import secure_user_dir
from blunder_tutor.web.per_user_cache import PerUserCache

log = logging.getLogger(__name__)


class BlunderTutorFilePermissionPolicy:
    """Production :class:`FilePermissionPolicy` for blunder_tutor: bridges
    the auth-core protocol to the project's POSIX hardening helpers
    (umask 077 + chmod 0600 on the auth DB and its WAL/SHM siblings).
    """

    def restrict_umask(self) -> AbstractContextManager[None]:
        return secure_fs.restrict_umask()

    def secure_db_file(self, path: Path) -> None:
        secure_fs.secure_db_file(path)


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
    cleaned the filesystem. Failures are logged but non-fatal: the
    auth row is already gone, so the dir is at worst an orphan that
    ``blunder-tutor auth prune-orphans`` will surface to the operator.
    """
    user_dir = users_dir / user_id
    if not user_dir.exists():
        return
    try:
        shutil.rmtree(user_dir)
    except OSError:
        log.exception("cleanup_user_dir: rmtree failed for %s", user_dir)


def make_after_delete_hook(
    users_dir: Path,
    *caches: PerUserCache,
) -> Callable[[UserId], Awaitable[None]]:
    """Compose :func:`cleanup_user_dir` with per-user cache invalidation
    into a single :class:`AuthService` ``on_after_delete`` hook. Caches
    are invalidated *before* the directory is removed: the auth row is
    already gone by the time this hook runs, so ordering across the
    two cleanup steps matters only insofar as nothing should observe
    a stale-cache hit for a deleted user. Both pieces are best-effort
    — neither failure surfaces as a 500 on the delete-account request.
    """

    async def hook(user_id: UserId) -> None:
        for cache in caches:
            cache.invalidate(user_id)
        await cleanup_user_dir(users_dir, user_id)

    return hook

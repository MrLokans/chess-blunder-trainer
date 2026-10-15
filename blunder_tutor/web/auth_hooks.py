from __future__ import annotations

import logging
import shutil
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from pathlib import Path

from blunder_tutor import secure_fs
from blunder_tutor.auth import User, UserId
from blunder_tutor.migrations import run_migrations
from blunder_tutor.web.per_user_cache import PerUserCache

log = logging.getLogger(__name__)


class BlunderTutorFilePermissionPolicy:
    def restrict_umask(self) -> AbstractContextManager[None]:
        return secure_fs.restrict_umask()

    def secure_db_file(self, path: Path) -> None:
        secure_fs.secure_db_file(path)


def resolve_user_db_path(users_dir: Path, user_id: UserId) -> Path:
    return users_dir / user_id / "main.sqlite3"


async def materialize_user_dir(users_dir: Path, user: User) -> None:
    user_db_path = resolve_user_db_path(users_dir, user.id)
    secure_fs.secure_user_dir(user_db_path.parent)
    run_migrations(user_db_path)


async def cleanup_user_dir(users_dir: Path, user_id: UserId) -> None:
    """Failures are logged, not fatal: leftovers surface via `auth prune-orphans`."""
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

    async def hook(user_id: UserId) -> None:  # noqa: WPS430 — factory returns this closure; captures `caches` and `users_dir`.
        for cache in caches:
            cache.invalidate(user_id)
        await cleanup_user_dir(users_dir, user_id)

    return hook

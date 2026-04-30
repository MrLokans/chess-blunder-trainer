from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger(__name__)

DB_FILE_MODE = 0o600
USER_DIR_MODE = 0o700
RESTRICTIVE_UMASK = 0o77


@contextmanager
def restrict_umask() -> Iterator[None]:
    """Temporarily tighten the process umask to ``0o77`` so any file
    *created* inside the block lands with mode ``0o600`` (for files) or
    ``0o700`` (for directories) before any attacker can read it.

    This closes the chmod race that the explicit :func:`secure_db_file`
    cannot: between ``sqlite3.connect()`` creating the file with
    umask-default ``0o644`` and the follow-up ``os.chmod``, a tight
    poll from a local attacker can read the file. Wrap the connect
    inside this context and the window disappears.
    """
    previous = os.umask(RESTRICTIVE_UMASK)
    try:
        yield
    finally:
        os.umask(previous)


# SQLite side-files — WAL journal, shared memory index, and the rollback
# journal — contain the same row data as the main file between writer
# checkpoints, so they need the same permission treatment. Miss any one
# and an attacker with filesystem read can recover bcrypt hashes and
# session tokens.
_SQLITE_SIDE_FILES = ("-wal", "-shm", "-journal")


def secure_db_file(path: Path) -> None:
    """chmod a SQLite database file (and its WAL/SHM/journal siblings) to
    owner-only read/write. Safe to call on non-existent paths — a missing
    file means nothing to harden. Does not fail the caller on chmod
    errors (e.g. read-only filesystem, non-POSIX host) — logs a warning
    instead, because the call happens during startup and the app should
    still boot on degraded filesystems.
    """
    _chmod_if_present(path, DB_FILE_MODE)
    for suffix in _SQLITE_SIDE_FILES:
        _chmod_if_present(path.with_name(path.name + suffix), DB_FILE_MODE)


def secure_user_dir(path: Path) -> None:
    """Create (if missing) and chmod a per-user data directory to 0700.
    Same error semantics as :func:`secure_db_file`.
    """
    path.mkdir(parents=True, exist_ok=True)
    _chmod_if_present(path, USER_DIR_MODE)


def _chmod_if_present(path: Path, mode: int) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, mode)
    except OSError as exc:
        log.warning("secure_fs: could not chmod %s to %o (%s)", path, mode, exc)

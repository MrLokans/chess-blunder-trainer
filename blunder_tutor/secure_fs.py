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
    """Tighten the umask to 0o77 for the body so created files land 0o600/0o700, closing
    the window between `sqlite3.connect()` creating the file and a follow-up chmod."""
    previous = os.umask(RESTRICTIVE_UMASK)
    try:
        yield
    finally:
        os.umask(previous)


# Side files hold the same row data between checkpoints; missing one would let a reader
# recover hashes and session tokens.
_SQLITE_SIDE_FILES = ("-wal", "-shm", "-journal")


def secure_db_file(path: Path) -> None:
    """Missing paths are skipped and chmod failures only warn, so startup survives
    read-only filesystems."""
    _chmod_if_present(path, DB_FILE_MODE)
    for suffix in _SQLITE_SIDE_FILES:
        _chmod_if_present(path.with_name(path.name + suffix), DB_FILE_MODE)


def secure_user_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _chmod_if_present(path, USER_DIR_MODE)


def _chmod_if_present(path: Path, mode: int) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, mode)
    except OSError as exc:
        log.warning("secure_fs: could not chmod %s to %o (%s)", path, mode, exc)

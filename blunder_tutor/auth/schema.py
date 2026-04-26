from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Protocol

import aiosqlite


class FilePermissionPolicy(Protocol):
    """Strategy for hardening auth DB file permissions during schema init.

    The auth core must not assume POSIX semantics (chmod, umask) since
    operators on Windows, networked filesystems, or ephemeral test dirs
    don't need or can't apply owner-only perms. Callers inject a policy
    that knows how their platform handles file permissions; the default
    :class:`NoOpFilePermissionPolicy` is safe everywhere.
    """

    def restrict_umask(self) -> AbstractContextManager[None]:
        """Sync context manager that tightens file-creation perms for
        the lifetime of the body. The schema connect runs inside this
        so the new file lands with restrictive perms before any chmod
        follow-up — closing the race between file create and chmod.
        """
        ...

    def secure_db_file(self, path: Path) -> None:
        """Belt-and-suspenders chmod after the file is created. Idempotent."""
        ...


class NoOpFilePermissionPolicy:
    """Default :class:`FilePermissionPolicy`: do nothing. Library-safe
    on any platform; consumers that need POSIX file hardening swap in
    their own implementation."""

    def restrict_umask(self) -> AbstractContextManager[None]:
        return nullcontext()

    def secure_db_file(self, path: Path) -> None:
        return None


_NOOP_POLICY: FilePermissionPolicy = NoOpFilePermissionPolicy()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    email        TEXT UNIQUE,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at   TEXT
);

CREATE TABLE IF NOT EXISTS identities (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    provider_subject  TEXT NOT NULL,
    credential        TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider, provider_subject)
);

CREATE INDEX IF NOT EXISTS identities_user_id_idx ON identities(user_id);

CREATE TABLE IF NOT EXISTS sessions (
    token         TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL DEFAULT (datetime('now')),
    user_agent    TEXT,
    ip_address    TEXT
);

CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS setup (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""


async def initialize_auth_schema(
    db_path: Path,
    policy: FilePermissionPolicy = _NOOP_POLICY,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with policy.restrict_umask():
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()
    policy.secure_db_file(db_path)

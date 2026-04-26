from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from blunder_tutor.auth import initialize_auth_schema
from blunder_tutor.migrations import run_migrations
from blunder_tutor.secure_fs import (
    DB_FILE_MODE,
    USER_DIR_MODE,
    secure_db_file,
    secure_user_dir,
)
from blunder_tutor.web.auth_hooks import BlunderTutorFilePermissionPolicy


def _mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


class TestSecureDbFile:
    def test_chmods_main_and_side_files_to_0600(self, tmp_path: Path):
        db = tmp_path / "x.sqlite3"
        db.write_bytes(b"")
        (tmp_path / "x.sqlite3-wal").write_bytes(b"")
        (tmp_path / "x.sqlite3-shm").write_bytes(b"")
        (tmp_path / "x.sqlite3-journal").write_bytes(b"")
        # Start from a world-readable state (0644) to prove the chmod
        # happens — the umask of the test runner varies.
        for p in (
            db,
            tmp_path / "x.sqlite3-wal",
            tmp_path / "x.sqlite3-shm",
            tmp_path / "x.sqlite3-journal",
        ):
            os.chmod(p, 0o644)

        secure_db_file(db)

        for p in (
            db,
            tmp_path / "x.sqlite3-wal",
            tmp_path / "x.sqlite3-shm",
            tmp_path / "x.sqlite3-journal",
        ):
            assert _mode(p) == DB_FILE_MODE, f"{p.name} mode {_mode(p):o}"

    def test_missing_paths_are_noop(self, tmp_path: Path):
        secure_db_file(tmp_path / "nope.sqlite3")  # must not raise


class TestSecureUserDir:
    def test_creates_and_chmods_to_0700(self, tmp_path: Path):
        d = tmp_path / "users" / "abc"
        secure_user_dir(d)
        assert d.is_dir()
        assert _mode(d) == USER_DIR_MODE


class TestMigrationsLockDown:
    def test_run_migrations_chmods_db_to_0600(self, tmp_path: Path):
        db = tmp_path / "main.sqlite3"
        run_migrations(db)
        assert db.exists()
        assert _mode(db) == DB_FILE_MODE, f"mode={_mode(db):o}"


class TestAuthSchemaLockDown:
    async def test_initialize_auth_schema_chmods_to_0600(self, tmp_path: Path):
        db = tmp_path / "auth.sqlite3"
        await initialize_auth_schema(db, BlunderTutorFilePermissionPolicy())
        assert db.exists()
        assert _mode(db) == DB_FILE_MODE, f"mode={_mode(db):o}"

    async def test_default_policy_is_noop(self, tmp_path: Path):
        # Library default must work on any platform without granting
        # any perms — consumers that need POSIX hardening pass their
        # own policy.
        db = tmp_path / "auth.sqlite3"
        await initialize_auth_schema(db)
        assert db.exists()
        # Whatever the umask gave us — we just verified the no-op path
        # didn't raise on a platform that supports stat().


# Linux + macOS honor chmod. Windows does not carry POSIX perms → skip.
if os.name == "nt":
    pytestmark = pytest.mark.skip("POSIX-only")

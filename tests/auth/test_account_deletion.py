from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI

from blunder_tutor.auth import AuthDb, SqliteStorage, initialize_auth_schema
from blunder_tutor.web.app import scan_orphans


class TestAccountDeletion:
    async def test_delete_removes_user_db_dir(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
        tmp_path: Path,
    ) -> None:
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 200, r.text
        user_id = r.json()["id"]
        user_dir = tmp_path / "users" / user_id
        assert user_dir.exists(), "signup should have materialized per-user dir"

        r = await client_credentials_mode.delete("/api/auth/account")
        assert r.status_code == 204

        assert not user_dir.exists(), (
            "account delete must remove the per-user directory; a leftover dir "
            "would become an orphan on next boot"
        )

        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 401, "session must be revoked after account delete"


class TestOrphanScan:
    async def test_logs_but_does_not_delete(self, tmp_path: Path, caplog) -> None:
        users_dir = tmp_path / "users"
        users_dir.mkdir()
        orphan = users_dir / ("a" * 32)
        orphan.mkdir()
        (orphan / "main.sqlite3").touch()

        db_path = tmp_path / "auth.sqlite3"
        await initialize_auth_schema(db_path)
        async with AuthDb(db_path) as auth_db:
            with caplog.at_level(logging.WARNING, logger="blunder_tutor.web.app"):
                await scan_orphans(SqliteStorage(auth_db).users, users_dir)

        assert orphan.exists(), (
            "scan_orphans is diagnostic only — a silent delete would destroy "
            "data after a partial restore from backup"
        )
        assert (orphan / "main.sqlite3").exists()
        assert any("orphan" in rec.message.lower() for rec in caplog.records)

    async def test_no_warnings_when_all_dirs_match_users(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
        credentials_app: FastAPI,
        caplog,
    ) -> None:
        """Re-scanning right after a real signup produces zero
        warnings; the dir created by ``register()`` is paired with
        a ``users`` row."""
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 200, r.text

        users_dir: Path = credentials_app.state.auth.users_dir
        users = credentials_app.state.auth.storage.users
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="blunder_tutor.web.app"):
            await scan_orphans(users, users_dir)

        orphan_records = [r for r in caplog.records if "orphan" in r.message.lower()]
        assert orphan_records == []

    async def test_ignores_non_user_id_shaped_dirs(
        self, tmp_path: Path, caplog
    ) -> None:
        """Operators sometimes stash backups or READMEs under
        ``users/``; those are not orphans, they're artefacts."""
        users_dir = tmp_path / "users"
        users_dir.mkdir()
        (users_dir / "backups").mkdir()
        (users_dir / "README").mkdir()
        (users_dir / ("z" * 31)).mkdir()  # almost user-id-shape, too short

        db_path = tmp_path / "auth.sqlite3"
        await initialize_auth_schema(db_path)
        async with AuthDb(db_path) as auth_db:
            with caplog.at_level(logging.WARNING, logger="blunder_tutor.web.app"):
                await scan_orphans(SqliteStorage(auth_db).users, users_dir)

        orphan_records = [r for r in caplog.records if "orphan" in r.message.lower()]
        assert orphan_records == []

    async def test_missing_users_dir_is_noop(self, tmp_path: Path, caplog) -> None:
        """A brand-new deployment has no ``users/`` yet — the scan must
        exit cleanly rather than raising."""
        db_path = tmp_path / "auth.sqlite3"
        await initialize_auth_schema(db_path)
        async with AuthDb(db_path) as auth_db:
            with caplog.at_level(logging.WARNING, logger="blunder_tutor.web.app"):
                await scan_orphans(
                    SqliteStorage(auth_db).users, tmp_path / "does-not-exist"
                )

        assert not (tmp_path / "does-not-exist").exists()
        orphan_records = [r for r in caplog.records if "orphan" in r.message.lower()]
        assert orphan_records == []

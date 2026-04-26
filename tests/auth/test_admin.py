"""Tests for the library admin surface (TREK-58 / EPIC-3 P4.3).

These exercise the functions in ``blunder_tutor.auth.cli.admin``
directly — no argparse, no SystemExit. Library callers (alternative
CLIs, web admin UIs, scripts) drive these the same way the
blunder_tutor CLI wrapper does.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from blunder_tutor.auth import (
    AuthDb,
    InviteCannotBeRegeneratedError,
    SqliteStorage,
    Username,
    UserNotFoundError,
    initialize_auth_schema,
    verify_invite_code,
)
from blunder_tutor.auth.cli import admin
from tests.helpers.auth import build_test_auth_service


@pytest.fixture
async def service_storage(tmp_path: Path):
    auth_db_path = tmp_path / "auth.sqlite3"
    await initialize_auth_schema(auth_db_path)
    auth_db = AuthDb(auth_db_path)
    await auth_db.connect()
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    storage = SqliteStorage(auth_db)
    service = build_test_auth_service(
        auth_db=auth_db,
        users_dir=users_dir,
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )
    try:
        yield service, storage
    finally:
        await auth_db.close()


class TestListUsers:
    async def test_returns_empty_list_initially(self, service_storage) -> None:
        service, _ = service_storage
        assert await admin.list_users(service) == []

    async def test_returns_registered_users(self, service_storage) -> None:
        service, _ = service_storage
        await service.register(username=Username("alice"), password="password123")
        users = await admin.list_users(service)
        assert [u.username for u in users] == ["alice"]


class TestResetPassword:
    async def test_replaces_credential_and_revokes_sessions(
        self, service_storage
    ) -> None:
        service, _ = service_storage
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        assert await service.resolve_session(session.token, None) is not None

        result = await admin.reset_password(
            service, Username("alice"), "new-password-xyz"
        )
        assert result.username == "alice"

        assert (
            await service.authenticate(
                "credentials",
                {"username": "alice", "password": "new-password-xyz"},
            )
            is not None
        )
        assert (
            await service.authenticate(
                "credentials",
                {"username": "alice", "password": "password123"},
            )
            is None
        )
        assert await service.resolve_session(session.token, None) is None

    async def test_unknown_user_raises_typed_error(self, service_storage) -> None:
        service, _ = service_storage
        with pytest.raises(UserNotFoundError) as excinfo:
            await admin.reset_password(service, Username("ghost"), "x" * 12)
        assert excinfo.value.username == "ghost"


class TestRevokeSessions:
    async def test_invalidates_all_sessions(self, service_storage) -> None:
        service, _ = service_storage
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        s1 = await service.create_session(user_id=user.id, user_agent=None, ip=None)
        s2 = await service.create_session(user_id=user.id, user_agent=None, ip=None)

        result = await admin.revoke_sessions(service, Username("alice"))
        assert result.username == "alice"

        assert await service.resolve_session(s1.token, None) is None
        assert await service.resolve_session(s2.token, None) is None

    async def test_unknown_user_raises_typed_error(self, service_storage) -> None:
        service, _ = service_storage
        with pytest.raises(UserNotFoundError):
            await admin.revoke_sessions(service, Username("ghost"))


class TestDeleteUser:
    async def test_removes_row_and_fires_after_delete_hook(
        self, service_storage, tmp_path: Path
    ) -> None:
        service, _ = service_storage
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        # The default test service wires `cleanup_user_dir` as on_after_delete.
        user_dir = tmp_path / "users" / user.id
        assert user_dir.exists()

        await admin.delete_user(service, Username("alice"))
        assert not user_dir.exists()

    async def test_unknown_user_raises_typed_error(self, service_storage) -> None:
        service, _ = service_storage
        with pytest.raises(UserNotFoundError):
            await admin.delete_user(service, Username("ghost"))


class TestRegenerateInvite:
    async def test_writes_fresh_code_when_no_users(self, service_storage) -> None:
        service, storage = service_storage
        secret_key = "x" * 32
        code = await admin.regenerate_invite(
            service, setup_repo=storage.setup, secret_key=secret_key
        )
        assert verify_invite_code(code, secret_key)
        assert await storage.setup.get("invite_code") == code

    async def test_refuses_when_users_already_exist(self, service_storage) -> None:
        service, storage = service_storage
        await service.register(username=Username("alice"), password="password123")
        with pytest.raises(InviteCannotBeRegeneratedError):
            await admin.regenerate_invite(
                service, setup_repo=storage.setup, secret_key="x" * 32
            )

from __future__ import annotations

import argparse as ap
import io
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.invite import verify_invite_code
from blunder_tutor.auth.schema import initialize_auth_schema
from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.storage_sqlite import SqliteStorage
from blunder_tutor.auth.types import Username
from blunder_tutor.cli.auth import (
    AuthCommand,
    _resolve_new_password,
    cmd_delete_user,
    cmd_list_users,
    cmd_prune_orphans,
    cmd_regenerate_invite,
    cmd_reset_password,
    cmd_revoke_sessions,
)
from tests.helpers.auth import build_test_auth_service


@pytest.fixture
async def ctx(tmp_path: Path):
    auth_db_path = tmp_path / "auth.sqlite3"
    await initialize_auth_schema(auth_db_path)
    auth_db = AuthDb(auth_db_path)
    await auth_db.connect()
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    service = build_test_auth_service(
        auth_db=auth_db,
        users_dir=users_dir,
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )
    try:
        yield {
            "storage": SqliteStorage(auth_db),
            "users_dir": users_dir,
            "service": service,
            "secret_key": "x" * 32,
        }
    finally:
        await auth_db.close()


class TestListUsers:
    async def test_empty(self, ctx, capsys) -> None:
        await cmd_list_users(ctx)
        out = capsys.readouterr().out
        assert "No users" in out

    async def test_after_signup(self, ctx, capsys) -> None:
        await ctx["service"].register(
            username=Username("alice"), password="password123"
        )
        await cmd_list_users(ctx)
        out = capsys.readouterr().out
        assert "alice" in out


class TestResetPassword:
    async def test_resets_and_revokes_sessions(self, ctx) -> None:
        service: AuthService = ctx["service"]
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        assert await service.resolve_session(session.token, None) is not None

        await cmd_reset_password(ctx, "alice", "new-password-xyz")

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

    async def test_unknown_user_exits(self, ctx) -> None:
        with pytest.raises(SystemExit, match="No such user"):
            await cmd_reset_password(ctx, "ghost", "new-password-xyz")


class TestResolveNewPassword:
    """The new-password value must never reach argparse. These guard
    the stdin + interactive-prompt paths in ``_resolve_new_password``.
    """

    def test_subparser_does_not_accept_positional_password(self):
        parser = ap.ArgumentParser()
        sub = parser.add_subparsers(dest="command", required=True)
        AuthCommand().register_subparser(sub)

        # `reset-password alice hunter2` used to be valid; now it must
        # fail because the positional is gone.
        with pytest.raises(SystemExit):
            parser.parse_args(["auth", "reset-password", "alice", "hunter2"])

        # Sanity: the new form with --password-stdin flag parses.
        ns = parser.parse_args(["auth", "reset-password", "alice", "--password-stdin"])
        assert ns.username == "alice"
        assert ns.password_stdin is True
        assert not hasattr(ns, "new_password")

    def test_password_stdin_reads_line(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("s3cret-password\n"))
        args = ap.Namespace(password_stdin=True)
        assert _resolve_new_password(args) == "s3cret-password"

    def test_password_stdin_empty_exits(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
        args = ap.Namespace(password_stdin=True)
        with pytest.raises(SystemExit, match="empty password"):
            _resolve_new_password(args)

    def test_interactive_prompts_twice_and_matches(self, monkeypatch):
        responses = iter(["new-password-xyz", "new-password-xyz"])
        monkeypatch.setattr(
            "blunder_tutor.cli.auth.getpass.getpass",
            lambda _prompt: next(responses),
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        args = ap.Namespace(password_stdin=False)
        assert _resolve_new_password(args) == "new-password-xyz"

    def test_interactive_mismatch_exits(self, monkeypatch):
        responses = iter(["pw-a", "pw-b"])
        monkeypatch.setattr(
            "blunder_tutor.cli.auth.getpass.getpass",
            lambda _prompt: next(responses),
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        args = ap.Namespace(password_stdin=False)
        with pytest.raises(SystemExit, match="did not match"):
            _resolve_new_password(args)

    def test_no_tty_refuses_to_fall_back_to_input(self, monkeypatch):
        """Without a TTY, getpass would silently call input() which
        echoes. Refuse explicitly so the operator sees a clear error
        instead of a password in scrollback."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        args = ap.Namespace(password_stdin=False)
        with pytest.raises(SystemExit, match="no TTY"):
            _resolve_new_password(args)


class TestRevokeSessions:
    async def test_revokes_all_tokens(self, ctx) -> None:
        service: AuthService = ctx["service"]
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        s1 = await service.create_session(user_id=user.id, user_agent=None, ip=None)
        s2 = await service.create_session(user_id=user.id, user_agent=None, ip=None)

        await cmd_revoke_sessions(ctx, "alice")

        assert await service.resolve_session(s1.token, None) is None
        assert await service.resolve_session(s2.token, None) is None

    async def test_unknown_user_exits(self, ctx) -> None:
        with pytest.raises(SystemExit, match="No such user"):
            await cmd_revoke_sessions(ctx, "ghost")


class TestDeleteUser:
    async def test_removes_row_and_directory(self, ctx) -> None:
        service: AuthService = ctx["service"]
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        user_dir = ctx["users_dir"] / user.id
        assert user_dir.exists()

        await cmd_delete_user(ctx, "alice")

        assert not user_dir.exists()
        assert (
            await service.authenticate(
                "credentials",
                {"username": "alice", "password": "password123"},
            )
            is None
        )

    async def test_unknown_user_exits(self, ctx) -> None:
        with pytest.raises(SystemExit, match="No such user"):
            await cmd_delete_user(ctx, "ghost")


class TestRegenerateInvite:
    async def test_writes_fresh_hmac_code(self, ctx, capsys) -> None:
        await cmd_regenerate_invite(ctx)
        out = capsys.readouterr().out.strip()
        assert out.startswith("New invite code: ")
        code = out.split(": ", 1)[1]
        assert verify_invite_code(code, ctx["secret_key"])

        assert await ctx["storage"].setup.get("invite_code") == code

    async def test_refuses_when_users_exist(self, ctx) -> None:
        await ctx["service"].register(
            username=Username("alice"), password="password123"
        )
        with pytest.raises(SystemExit, match="users already exist"):
            await cmd_regenerate_invite(ctx)


class TestPruneOrphans:
    async def test_removes_only_unknown_dirs(self, ctx, capsys) -> None:
        service: AuthService = ctx["service"]
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        kept = ctx["users_dir"] / user.id
        orphan = ctx["users_dir"] / ("b" * 32)
        orphan.mkdir()
        (orphan / "main.sqlite3").touch()

        await cmd_prune_orphans(ctx)

        assert kept.exists()
        assert not orphan.exists()
        out = capsys.readouterr().out
        assert "Removed 1 orphan" in out

    async def test_reports_zero_when_clean(self, ctx, capsys) -> None:
        await ctx["service"].register(
            username=Username("alice"), password="password123"
        )
        await cmd_prune_orphans(ctx)
        out = capsys.readouterr().out
        assert "Removed 0 orphan" in out

    async def test_missing_users_dir_is_noop(self, ctx, capsys) -> None:
        shutil.rmtree(ctx["users_dir"])
        await cmd_prune_orphans(ctx)
        out = capsys.readouterr().out
        assert "Removed 0 orphan" in out

    async def test_ignores_non_user_id_shaped_dirs(self, ctx, capsys) -> None:
        """Prune must never touch operator-owned artefacts like
        ``users/backups`` or ``users/README`` even when the user
        table is empty (the refuse-when-empty guard only applies to
        user-id-shaped candidates)."""
        (ctx["users_dir"] / "backups").mkdir()
        (ctx["users_dir"] / "README").mkdir()
        await cmd_prune_orphans(ctx)
        out = capsys.readouterr().out
        assert "Removed 0 orphan" in out
        assert (ctx["users_dir"] / "backups").exists()
        assert (ctx["users_dir"] / "README").exists()

    async def test_refuses_when_users_empty_but_dirs_exist(self, ctx, capsys) -> None:
        """A fresh auth DB paired with a populated ``users/`` is the
        tell-tale sign of a misconfigured DB_PATH. Silently pruning
        would wipe every user's data — refuse instead."""
        (ctx["users_dir"] / ("c" * 32)).mkdir()
        (ctx["users_dir"] / ("d" * 32)).mkdir()
        with pytest.raises(SystemExit, match="Refusing to prune"):
            await cmd_prune_orphans(ctx)
        assert (ctx["users_dir"] / ("c" * 32)).exists()
        assert (ctx["users_dir"] / ("d" * 32)).exists()

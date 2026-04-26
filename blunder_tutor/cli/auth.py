"""``blunder-tutor auth <sub>`` — argparse glue around the library's
admin functions in :mod:`blunder_tutor.auth.cli.admin`.

The actual operations live in the library; this module is the
operator-facing wrapper: argparse subparsers, password resolution
that keeps the new password off argv, and translation of typed
:class:`AuthError` subclasses into operator-friendly
``SystemExit`` messages.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import shutil
import sys
from datetime import timedelta
from functools import partial
from pathlib import Path

from blunder_tutor.auth import (
    CREDENTIALS_PROVIDER_NAME,
    AuthDb,
    AuthService,
    BcryptHasher,
    CredentialsProvider,
    HmacInvitePolicy,
    InviteCannotBeRegeneratedError,
    MaxUsersQuota,
    NoCredentialsIdentityError,
    SqliteStorage,
    UserNotFoundError,
    ValidationRules,
    admin,
    initialize_auth_schema,
    is_user_id_shape,
    make_username,
)
from blunder_tutor.cli.base import CLICommand
from blunder_tutor.web.auth_hooks import (
    BlunderTutorFilePermissionPolicy,
    cleanup_user_dir,
    materialize_user_dir,
)
from blunder_tutor.web.config import AppConfig


async def cmd_list_users(ctx: dict) -> None:
    users = await admin.list_users(ctx["service"])
    if not users:
        print("No users")
        return
    for u in users:
        print(f"{u.id}\t{u.username}\t{u.email or '-'}\t{u.created_at.isoformat()}")


async def cmd_reset_password(ctx: dict, username: str, new_password: str) -> None:
    try:
        await admin.reset_password(
            ctx["service"], make_username(username), new_password
        )
    except UserNotFoundError as exc:
        raise SystemExit(f"No such user: {exc.username}") from exc
    except NoCredentialsIdentityError as exc:
        raise SystemExit(f"User {exc.username} has no credentials identity") from exc
    print(f"Password reset for {username}; all sessions revoked.")


async def cmd_revoke_sessions(ctx: dict, username: str) -> None:
    try:
        await admin.revoke_sessions(ctx["service"], make_username(username))
    except UserNotFoundError as exc:
        raise SystemExit(f"No such user: {exc.username}") from exc
    print(f"Sessions revoked for {username}")


async def cmd_delete_user(ctx: dict, username: str) -> None:
    try:
        await admin.delete_user(ctx["service"], make_username(username))
    except UserNotFoundError as exc:
        raise SystemExit(f"No such user: {exc.username}") from exc
    print(f"Deleted {username}")


async def cmd_regenerate_invite(ctx: dict) -> None:
    try:
        code = await admin.regenerate_invite(
            ctx["service"],
            setup_repo=ctx["storage"].setup,
            secret_key=ctx["secret_key"],
        )
    except InviteCannotBeRegeneratedError as exc:
        raise SystemExit("Cannot regenerate invite: users already exist") from exc
    print(f"New invite code: {code}")


async def cmd_prune_orphans(ctx: dict) -> None:
    """Per-user data dirs are a blunder_tutor concept — auth core
    knows nothing about filesystem layout (validates the EPIC-3 P3.1
    seam). The library admin module deliberately does not expose
    ``prune_orphans``; it stays here next to the other dir-aware
    helpers in ``web/auth_hooks.py``.
    """
    users = ctx["storage"].users
    known = {u.id for u in await users.list_all()}
    users_dir: Path = ctx["users_dir"]
    removed = 0
    if not users_dir.exists():
        print("Removed 0 orphan directories")
        return

    # Refuse to act on what looks like a misconfigured DB_PATH: an
    # empty `users` table paired with existing per-user directories
    # almost always means the auth DB is fresh but the data dirs are
    # real. Running `rmtree` here would destroy every user's data.
    candidates = [
        c for c in users_dir.iterdir() if c.is_dir() and is_user_id_shape(c.name)
    ]
    if not known and candidates:
        raise SystemExit(
            f"Refusing to prune: auth DB has zero users but {users_dir} "
            f"contains {len(candidates)} user-id-shaped director"
            f"{'y' if len(candidates) == 1 else 'ies'}. "
            "Check DB_PATH — this looks like a misconfiguration."
        )

    for child in candidates:
        if child.name not in known:
            shutil.rmtree(child)
            removed += 1
    print(f"Removed {removed} orphan director{'y' if removed == 1 else 'ies'}")


_DISPATCH = {
    "list-users": (cmd_list_users, ()),
    # ``new_password`` is populated from stdin or getpass in the
    # dispatcher, not from argparse — passwords must not appear on argv.
    "reset-password": (cmd_reset_password, ("username", "new_password")),
    "revoke-sessions": (cmd_revoke_sessions, ("username",)),
    "delete-user": (cmd_delete_user, ("username",)),
    "regenerate-invite": (cmd_regenerate_invite, ()),
    "prune-orphans": (cmd_prune_orphans, ()),
}


def _resolve_new_password(args: argparse.Namespace) -> str:
    """Read the new password from stdin (non-interactive) or prompt twice
    via ``getpass`` (interactive). Never consults ``args.new_password``
    because argparse doesn't expose it — the flag was intentionally
    removed to prevent the value from landing on argv.
    """
    if getattr(args, "password_stdin", False):
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            raise SystemExit("reset-password: empty password on stdin")
        return password
    # `getpass` silently falls back to `input()` when no TTY is
    # attached — and `input()` echoes. Refuse explicitly so an
    # operator running e.g. ``docker exec container auth reset-password
    # alice`` (no ``-it``) gets a clear error instead of typing a
    # password that appears in scrollback.
    if not sys.stdin.isatty():
        raise SystemExit(
            "reset-password: no TTY attached. Use --password-stdin "
            "to feed the password from a secure source, e.g.: "
            "printf '%s' \"$NEW_PW\" | ... auth reset-password <user> --password-stdin"
        )
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("reset-password: passwords did not match")
    if not password:
        raise SystemExit("reset-password: password must not be empty")
    return password


class AuthCommand(CLICommand):
    """`blunder-tutor auth <sub>` — operator tools for the credentials
    auth backend. All subcommands are no-ops outside ``AUTH_MODE=credentials``
    since there is no auth.sqlite3 to act on."""

    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "auth"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        if config.auth.mode != "credentials":
            raise SystemExit("`auth` subcommands require AUTH_MODE=credentials")
        auth_db_path = config.data.db_path.parent / "auth.sqlite3"
        users_dir = config.data.db_path.parent / "users"
        users_dir.mkdir(parents=True, exist_ok=True)

        await initialize_auth_schema(auth_db_path, BlunderTutorFilePermissionPolicy())
        auth_db = AuthDb(auth_db_path)
        await auth_db.connect()
        try:
            rules = ValidationRules.default()
            hasher = BcryptHasher(rules, cost=config.auth.bcrypt_cost)
            storage = SqliteStorage(auth_db)
            service = AuthService(
                storage=storage,
                providers={
                    CREDENTIALS_PROVIDER_NAME: CredentialsProvider(
                        identities=storage.identities, hasher=hasher, rules=rules
                    ),
                },
                hasher=hasher,
                quota=MaxUsersQuota(config.auth.max_users),
                invite_policy=HmacInvitePolicy(setup_repo=storage.setup),
                on_after_register=partial(materialize_user_dir, users_dir),
                on_after_delete=partial(cleanup_user_dir, users_dir),
                session_max_age=timedelta(seconds=config.auth.session_max_age_seconds),
                session_idle=timedelta(seconds=config.auth.session_idle_seconds),
            )
            ctx = {
                "storage": storage,
                "users_dir": users_dir,
                "service": service,
                "secret_key": config.auth.secret_key,
            }
            await self._dispatch(args, ctx)
        finally:
            await auth_db.close()

    async def _dispatch(self, args: argparse.Namespace, ctx: dict) -> None:
        # reset-password reads the new password from a non-argv source so
        # it never appears in `ps`, shell history, or journald. Stdin mode
        # is for piped/scripted invocation; interactive falls through to
        # getpass with a confirmation prompt.
        if args.auth_subcommand == "reset-password":
            args.new_password = _resolve_new_password(args)
        fn, arg_names = _DISPATCH[args.auth_subcommand]
        await fn(ctx, *(getattr(args, name) for name in arg_names))

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        auth_parser = subparsers.add_parser(
            "auth", help="Manage auth users, sessions, and invite codes"
        )
        auth_subs = auth_parser.add_subparsers(dest="auth_subcommand", required=True)

        auth_subs.add_parser("list-users", help="Print all users")

        reset = auth_subs.add_parser(
            "reset-password",
            help="Set a new password for a user and revoke all their sessions",
        )
        reset.add_argument("username")
        reset.add_argument(
            "--password-stdin",
            action="store_true",
            help="Read the new password from stdin. Default is an "
            "interactive getpass prompt with confirmation. The new "
            "password is never accepted as a CLI argument.",
        )

        revoke = auth_subs.add_parser(
            "revoke-sessions",
            help="Invalidate every active session for a user",
        )
        revoke.add_argument("username")

        delete = auth_subs.add_parser(
            "delete-user",
            help="Hard-delete a user, their sessions, and their data directory",
        )
        delete.add_argument("username")

        auth_subs.add_parser(
            "regenerate-invite",
            help="Mint a new first-user invite code (refuses if any users exist)",
        )

        auth_subs.add_parser(
            "prune-orphans",
            help="Delete per-user data directories that have no matching user row",
        )

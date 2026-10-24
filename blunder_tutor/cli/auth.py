from __future__ import annotations

import argparse
import asyncio
import getpass
import shutil
import sys
from datetime import timedelta
from functools import partial
from pathlib import Path

from blunder_tutor.auth import (  # noqa: WPS235 — operator CLI consumes the public auth namespace surface to wire AuthService + admin + invite policy in one place.
    CREDENTIALS_PROVIDER_NAME,
    AuthDb,
    AuthService,
    BcryptHasher,
    CredentialsProvider,
    HmacInvitePolicy,
    InviteCannotBeRegeneratedError,
    MaxUsersQuota,
    NoCredentialsIdentityError,
    SessionConfig,
    SqliteStorage,
    UserNotFoundError,
    ValidationRules,
    admin,
    initialize_auth_schema,
    is_user_id_shape,
    make_username,
)
from blunder_tutor.cli.base import CLICommand
from blunder_tutor.constants import AUTH_MODE_CREDENTIALS
from blunder_tutor.web.auth_hooks import (
    BlunderTutorFilePermissionPolicy,
    cleanup_user_dir,
    materialize_user_dir,
)
from blunder_tutor.web.config import AppConfig


async def cmd_list_users(ctx: dict) -> None:
    users = await admin.list_users(ctx["service"])  # noqa: WPS226 — `service` is the conventional context dict key, used by every cmd_* function.
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
    """Lives here, not in the auth library, because per-user dirs are a blunder_tutor
    concept."""
    users = ctx["storage"].users
    known = {u.id for u in await users.list_all()}
    users_dir: Path = ctx["users_dir"]
    removed = 0
    if not users_dir.exists():
        print("Removed 0 orphan directories")
        return

    # Refuse when `users` is empty but per-user dirs exist: likely a misconfigured
    # DB_PATH, and rmtree would destroy real data.
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


_DISPATCH = frozendict(
    {
        "list-users": (cmd_list_users, ()),
        # Populated from stdin or getpass, never argparse: passwords must not appear on
        # argv.
        "reset-password": (cmd_reset_password, ("username", "new_password")),  # noqa: WPS226 — argparse positional name `username`; identical signature across user-management subcommands.
        "revoke-sessions": (cmd_revoke_sessions, ("username",)),
        "delete-user": (cmd_delete_user, ("username",)),
        "regenerate-invite": (cmd_regenerate_invite, ()),
        "prune-orphans": (cmd_prune_orphans, ()),
    }
)


def _read_password_interactive() -> str:
    # `getpass` falls back to `input()` (which echoes) without a TTY; refuse, e.g.
    # `docker exec` without `-it`.
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


def _resolve_new_password(args: argparse.Namespace) -> str:
    """No argv flag by design, to keep the password out of process listings."""
    if getattr(args, "password_stdin", False):
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            raise SystemExit("reset-password: empty password on stdin")
        return password
    return _read_password_interactive()


class AuthCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "auth"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

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

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        if config.auth.mode != AUTH_MODE_CREDENTIALS:
            raise SystemExit("`auth` subcommands require AUTH_MODE=credentials")
        auth_db_path = config.data.db_path.parent / "auth.sqlite3"
        users_dir = config.data.db_path.parent / "users"
        users_dir.mkdir(parents=True, exist_ok=True)

        await initialize_auth_schema(auth_db_path, BlunderTutorFilePermissionPolicy())
        async with AuthDb(auth_db_path) as auth_db:
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
                session_config=SessionConfig(
                    max_age=timedelta(seconds=config.auth.session_max_age_seconds),
                    idle=timedelta(seconds=config.auth.session_idle_seconds),
                ),
                on_after_register=partial(materialize_user_dir, users_dir),
                on_after_delete=partial(cleanup_user_dir, users_dir),
            )
            ctx = {
                "storage": storage,
                "users_dir": users_dir,
                "service": service,
                "secret_key": config.auth.secret_key,
            }
            await self._dispatch(args, ctx)

    async def _dispatch(self, args: argparse.Namespace, ctx: dict) -> None:
        if args.auth_subcommand == "reset-password":
            args.new_password = _resolve_new_password(args)
        fn, arg_names = _DISPATCH[args.auth_subcommand]
        await fn(ctx, *(getattr(args, name) for name in arg_names))

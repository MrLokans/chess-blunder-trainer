from __future__ import annotations

import hmac
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.invite import verify_invite_code
from blunder_tutor.auth.providers.base import AuthProvider
from blunder_tutor.auth.providers.credentials import CredentialsProvider
from blunder_tutor.auth.repository import (
    IdentityRepository,
    SessionRepository,
    UserRepository,
    _now_iso,
)
from blunder_tutor.auth.types import (
    DuplicateEmailError,
    DuplicateUsernameError,
    Email,
    Identity,
    InvalidInviteCodeError,
    ProviderName,
    Session,
    SessionToken,
    User,
    UserCapReachedError,
    UserContext,
    UserId,
    Username,
    hash_password,
    make_identity_id,
    make_session_token,
    make_user_id,
)
from blunder_tutor.migrations import run_migrations


class AuthService:
    """Service layer for all auth operations.

    Owns a single :class:`AuthDb` (one connection, one write lock) and
    shares it with every repository and provider — so concurrent
    register/login calls serialize correctly and multi-statement
    operations (register, delete_account) run in one transaction.
    """

    def __init__(
        self,
        *,
        auth_db: AuthDb,
        users_dir: Path,
        session_max_age: timedelta,
        session_idle: timedelta,
    ) -> None:
        self._db = auth_db
        self._users_dir = users_dir
        self._session_max_age = session_max_age
        self._session_idle = session_idle
        self._users = UserRepository(db=auth_db)
        self._identities = IdentityRepository(db=auth_db)
        self._sessions = SessionRepository(db=auth_db)
        self._providers: dict[ProviderName, AuthProvider] = {
            "credentials": CredentialsProvider(identities=self._identities),
        }

    async def register(
        self,
        *,
        username: Username,
        password: str,
        email: Email | None = None,
    ) -> User:
        # Hash outside the transaction — bcrypt is slow (~100ms) and we don't
        # want to hold the write lock for that long. This also surfaces
        # InvalidPasswordError before we touch the DB.
        credential = hash_password(password)
        user_id = make_user_id()
        now = _now_iso()
        identity_id = make_identity_id()

        try:
            async with self._db.transaction() as conn:
                await conn.execute(
                    "INSERT INTO users (id, username, email, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, username, email, now),
                )
                await conn.execute(
                    "INSERT INTO identities "
                    "(id, user_id, provider, provider_subject, credential, created_at) "
                    "VALUES (?, ?, 'credentials', ?, ?, ?)",
                    (identity_id, user_id, username, credential, now),
                )
        except sqlite3.IntegrityError as exc:
            # UNIQUE constraint violation — reclassify as a domain error.
            message = str(exc)
            if "users.username" in message:
                raise DuplicateUsernameError(username) from exc
            if "users.email" in message:
                raise DuplicateEmailError(email or "") from exc
            raise

        # Materialize the per-user data DB after the auth rows commit.
        # run_migrations is sync + idempotent, safe to call on a missing
        # file. Trade-off: if migrations fail mid-way, the user + identity
        # rows already exist in auth.sqlite3 — the user can authenticate
        # but has no data dir, and subsequent requests will 500. We accept
        # this over (a) holding the auth write-lock for a multi-second sync
        # operation, or (b) compensating rollback that duplicates logic
        # already in CASCADE. Phase 4 may move migration to lazy-on-first
        # -access inside `get_db_path` to close the gap entirely.
        user_db_path = self.db_path_for(user_id)
        user_db_path.parent.mkdir(parents=True, exist_ok=True)
        run_migrations(user_db_path)

        user = await self._users.get_by_id(user_id)
        assert user is not None
        return user

    async def signup(
        self,
        *,
        username: Username,
        password: str,
        max_users: int,
        email: Email | None = None,
        invite_code: str | None = None,
        secret_key: str | None = None,
    ) -> User:
        """Atomic signup path for the HTTP surface.

        Cap enforcement and first-user invite-consume happen inside the
        same ``BEGIN IMMEDIATE`` transaction as the ``users`` /
        ``identities`` INSERTs. Without this, two concurrent POSTs to
        ``/api/auth/signup`` could both pass an API-level cap check and
        both commit, exceeding ``max_users``. Single-transaction gating
        makes the cap a DB invariant instead of a best-effort check.

        ``register`` is the lower-level API and stays usable from tests
        that don't care about cap/invite.
        """
        credential = hash_password(password)
        user_id = make_user_id()
        identity_id = make_identity_id()
        now = _now_iso()

        try:
            async with self._db.transaction() as conn:
                async with conn.execute(
                    "SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"
                ) as cur:
                    row = await cur.fetchone()
                count = int(row[0]) if row else 0

                if count >= max_users:
                    raise UserCapReachedError()

                first_user = count == 0
                if first_user:
                    if not invite_code:
                        raise InvalidInviteCodeError("missing")
                    async with conn.execute(
                        "SELECT value FROM setup WHERE key = 'invite_code'"
                    ) as cur:
                        stored_row = await cur.fetchone()
                    if stored_row is None:
                        raise InvalidInviteCodeError("not_issued")
                    stored = stored_row[0]
                    # Two checks: the stored-equality enforces single-use
                    # (already-consumed invites fail even if HMAC-valid),
                    # the HMAC verifies authenticity against the server
                    # secret (a hand-crafted "<payload>.<sig>" with the
                    # right shape but wrong secret fails here).
                    if not hmac.compare_digest(invite_code, stored):
                        raise InvalidInviteCodeError("rotated")
                    if not verify_invite_code(invite_code, secret_key or ""):
                        raise InvalidInviteCodeError("hmac")

                await conn.execute(
                    "INSERT INTO users (id, username, email, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, username, email, now),
                )
                await conn.execute(
                    "INSERT INTO identities "
                    "(id, user_id, provider, provider_subject, credential, created_at) "
                    "VALUES (?, ?, 'credentials', ?, ?, ?)",
                    (identity_id, user_id, username, credential, now),
                )
                if first_user:
                    await conn.execute("DELETE FROM setup WHERE key = 'invite_code'")
        except sqlite3.IntegrityError as exc:
            message = str(exc)
            if "users.username" in message:
                raise DuplicateUsernameError(username) from exc
            if "users.email" in message:
                raise DuplicateEmailError(email or "") from exc
            raise

        user_db_path = self.db_path_for(user_id)
        user_db_path.parent.mkdir(parents=True, exist_ok=True)
        run_migrations(user_db_path)

        user = await self._users.get_by_id(user_id)
        assert user is not None
        return user

    async def authenticate(
        self, provider: ProviderName, credentials: dict[str, str]
    ) -> User | None:
        prov = self._providers.get(provider)
        if prov is None:
            return None
        identity = await prov.authenticate(credentials)
        if identity is None:
            return None
        return await self._users.get_by_id(identity.user_id)

    async def create_session(
        self,
        *,
        user_id: UserId,
        user_agent: str | None,
        ip: str | None,
    ) -> Session:
        token = make_session_token()
        expires_at = datetime.now(UTC) + self._session_max_age
        await self._sessions.insert(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip,
        )
        session = await self._sessions.get(token)
        assert session is not None
        return session

    async def resolve_session(self, token: str, ip: str | None) -> UserContext | None:
        if not token:
            return None
        typed_token = SessionToken(token)
        session = await self._sessions.get(typed_token)
        if session is None:
            return None
        now = datetime.now(UTC)
        if session.expires_at < now:
            await self._sessions.delete(typed_token)
            return None
        if session.last_seen_at + self._session_idle < now:
            await self._sessions.delete(typed_token)
            return None
        await self._sessions.bump_last_seen(typed_token)
        user = await self._users.get_by_id(session.user_id)
        if user is None:
            # Session row orphaned — referential integrity should prevent
            # this, but don't trust it as a security invariant.
            await self._sessions.delete(typed_token)
            return None
        return UserContext(
            user_id=user.id,
            username=user.username,
            db_path=self.db_path_for(user.id),
            session_token=typed_token,
        )

    async def revoke_session(self, token: str) -> None:
        await self._sessions.delete(SessionToken(token))

    async def revoke_all_sessions(self, user_id: UserId) -> None:
        await self._sessions.delete_all_for_user(user_id)

    async def delete_account(self, user_id: UserId) -> None:
        # ON DELETE CASCADE handles identities + sessions in a single
        # statement. rmtree runs AFTER commit: if the FS op fails, the
        # user is already logged out and cannot log back in — the orphan
        # directory is a disk-space nuisance, not a data-integrity bug.
        # Inverse ordering could leave a live user with no data dir.
        async with self._db.transaction() as conn:
            await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        user_dir = self._users_dir / user_id
        if user_dir.exists():
            shutil.rmtree(user_dir)

    async def user_count(self) -> int:
        return await self._users.count()

    async def get_user(self, user_id: UserId) -> User | None:
        return await self._users.get_by_id(user_id)

    async def identities_for(self, user_id: UserId) -> list[Identity]:
        return await self._identities.list_for_user(user_id)

    async def list_sessions(self, user_id: UserId) -> list[Session]:
        return await self._sessions.list_for_user(user_id)

    def db_path_for(self, user_id: UserId) -> Path:
        return self._users_dir / user_id / "main.sqlite3"

    async def close(self) -> None:
        for prov in self._providers.values():
            await prov.close()
        # The shared connection is owned by the AuthDb — callers that
        # created the AuthDb are responsible for closing it. This keeps
        # lifecycle in one place and avoids use-after-close when the
        # same AuthDb is reused (e.g. CLI commands in the same process).

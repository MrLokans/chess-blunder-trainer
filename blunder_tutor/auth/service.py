from __future__ import annotations

import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from blunder_tutor.auth.db import AuthDb
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
    ProviderName,
    Session,
    SessionToken,
    User,
    UserContext,
    UserId,
    Username,
    hash_password,
    make_identity_id,
    make_session_token,
    make_user_id,
)


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
        # Deliberately no token-shape pre-check: any early return would be a
        # timing fork distinguishing "malformed token" from "unknown token".
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

    def db_path_for(self, user_id: UserId) -> Path:
        return self._users_dir / user_id / "main.sqlite3"

    async def close(self) -> None:
        for prov in self._providers.values():
            await prov.close()
        # The shared connection is owned by the AuthDb — callers that
        # created the AuthDb are responsible for closing it. This keeps
        # lifecycle in one place and avoids use-after-close when the
        # same AuthDb is reused (e.g. CLI commands in the same process).

from __future__ import annotations

import sqlite3
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, NoReturn

from blunder_tutor.auth.core.protocols import (
    InvitePolicy,
    PasswordHasher,
    QuotaPolicy,
    Storage,
)
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    DuplicateEmailError,
    DuplicateUsernameError,
    SessionToken,
    UserCapReachedError,
    UserContext,
    make_identity_id,
    make_session_token,
    make_user_id,
)
from blunder_tutor.auth.providers import AuthProvider
from blunder_tutor.utils.time import now_iso

if TYPE_CHECKING:
    from blunder_tutor.auth.core.types import (
        Email,
        Identity,
        IdentityId,
        PasswordHash,
        ProviderName,
        Session,
        User,
        UserId,
        Username,
    )


async def _noop_after_register(_user: User) -> None:
    pass


async def _noop_after_delete(_user_id: UserId) -> None:
    pass


def _translate_integrity_error(
    exc: sqlite3.IntegrityError,
    username: Username,
    email: Email | None,
) -> NoReturn:
    message = str(exc)
    if "users.username" in message:
        raise DuplicateUsernameError(username) from exc
    if "users.email" in message:
        raise DuplicateEmailError(email or "") from exc
    raise exc


@dataclass(frozen=True, kw_only=True)
class SessionConfig:
    """`kw_only`: both fields are timedelta and a positional swap would silently invert
    them."""

    max_age: timedelta
    idle: timedelta


class AuthService:
    def __init__(
        self,
        *,
        storage: Storage,
        providers: Mapping[ProviderName, AuthProvider],
        hasher: PasswordHasher,
        quota: QuotaPolicy,
        invite_policy: InvitePolicy,
        session_config: SessionConfig,
        on_after_register: Callable[[User], Awaitable[None]] = _noop_after_register,
        on_after_delete: Callable[[UserId], Awaitable[None]] = _noop_after_delete,
    ) -> None:
        self._storage = storage
        self._on_after_register = on_after_register
        self._on_after_delete = on_after_delete
        self._session_max_age = session_config.max_age
        self._session_idle = session_config.idle
        self._users = storage.users
        self._identities = storage.identities
        self._sessions = storage.sessions
        self._providers: dict[ProviderName, AuthProvider] = dict(providers)
        self._hasher = hasher
        self._quota = quota
        self._invite_policy = invite_policy
        # Warm the dummy hash so the first authenticate takes the same time as later
        # ones.
        hasher.dummy_hash()

    async def signup(
        self,
        *,
        username: Username,
        password: str,
        email: Email | None = None,
        invite_code: str | None = None,
    ) -> User:
        """Atomic signup: quota check and invite consume run in the same `BEGIN IMMEDIATE`
        transaction as the inserts, so concurrent signups cannot exceed the cap."""
        credential = self._hasher.hash(password)
        user_id = make_user_id()
        now = now_iso()
        try:
            async with self._storage.transaction() as conn:
                # `count()` runs inside the open `BEGIN IMMEDIATE` on the same
                # connection, so concurrent signups serialize and the cap is a DB
                # invariant.
                count = await self._users.count()
                if not self._quota.allow_signup(count):
                    raise UserCapReachedError()
                await self._invite_policy.consume(conn, invite_code, count)
                await self._insert_user_with_credential(
                    conn,
                    user_id=user_id,
                    username=username,
                    email=email,
                    credential=credential,
                    now=now,
                )
        except sqlite3.IntegrityError as exc:
            _translate_integrity_error(exc, username, email)
        return await self._finalize_registration(user_id)

    def register_provider(self, provider: AuthProvider) -> None:
        self._providers[provider.name] = provider

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
        session = await self._load_live_session(typed_token)
        if session is None:
            return None
        await self._maybe_bump_last_seen(typed_token, session)
        user = await self._users.get_by_id(session.user_id)
        if user is None:
            # Orphaned session row: referential integrity should prevent this, but don't
            # rely on it for security.
            await self._sessions.delete(typed_token)
            return None
        return UserContext(
            user_id=user.id,
            username=user.username,
            session_token=typed_token,
        )

    async def revoke_session(self, token: str) -> None:
        await self._sessions.delete(SessionToken(token))

    async def revoke_all_sessions(self, user_id: UserId) -> None:
        await self._sessions.delete_all_for_user(user_id)

    async def delete_account(self, user_id: UserId) -> None:
        # Single statement: ON DELETE CASCADE removes identities and sessions
        # atomically, which needs `PRAGMA foreign_keys = ON` (set in `AuthDb.connect`).
        #
        # The hook runs after commit: if it fails the user is already gone, and leftover
        # external resources are a nuisance, not an integrity bug.
        await self._users.delete(user_id)
        await self._on_after_delete(user_id)

    async def user_count(self) -> int:
        return await self._users.count()

    async def get_user(self, user_id: UserId) -> User | None:
        return await self._users.get_by_id(user_id)

    async def get_user_by_username(self, username: Username) -> User | None:
        return await self._users.get_by_username(username)

    async def list_users(self) -> list[User]:
        return await self._users.list_all()

    async def identities_for(self, user_id: UserId) -> list[Identity]:
        return await self._identities.list_for_user(user_id)

    async def list_sessions(self, user_id: UserId) -> list[Session]:
        return await self._sessions.list_for_user(user_id)

    async def change_password(
        self,
        *,
        user_id: UserId,
        identity_id: IdentityId,
        new_password: str,
    ) -> None:
        """Also revokes every session (OWASP V7); use `IdentityRepo.update_credential` to
        skip that."""
        hashed = self._hasher.hash(new_password)
        await self._identities.update_credential(identity_id, hashed)
        await self._sessions.delete_all_for_user(user_id)

    async def _insert_user_with_credential(
        self,
        conn,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
        credential: PasswordHash,
        now: str,
    ) -> None:
        await self._users.insert_in_transaction(
            conn,
            user_id=user_id,
            username=username,
            email=email,
            created_at=now,
        )
        await self._identities.insert_in_transaction(
            conn,
            identity_id=make_identity_id(),
            user_id=user_id,
            provider=CREDENTIALS_PROVIDER_NAME,
            provider_subject=username,
            credential=credential,
            created_at=now,
        )

    async def _finalize_registration(self, user_id: UserId) -> User:
        """Run the `on_after_register` hook after commit.

        If the hook fails the user already exists but its external resources (per-user
        DB) may be missing. Accepted over holding the write lock during slow hooks or a
        compensating rollback."""
        user = await self._users.get_by_id(user_id)
        assert user is not None
        await self._on_after_register(user)
        return user

    async def _load_live_session(self, typed_token: SessionToken) -> Session | None:
        session = await self._sessions.get(typed_token)
        if session is None:
            return None
        now = datetime.now(UTC)
        absolute_expired = session.expires_at < now
        idle_expired = session.last_seen_at + self._session_idle < now
        if absolute_expired or idle_expired:
            await self._sessions.delete(typed_token)
            return None
        return session

    async def _maybe_bump_last_seen(
        self, typed_token: SessionToken, session: Session
    ) -> None:
        # Debounce `last_seen` writes so authenticated requests don't queue behind the
        # auth write lock: bump only past `idle / 10` (~17h at the 7-day default).
        bump_threshold = self._session_idle / 10
        if datetime.now(UTC) - session.last_seen_at >= bump_threshold:
            await self._sessions.bump_last_seen(typed_token)

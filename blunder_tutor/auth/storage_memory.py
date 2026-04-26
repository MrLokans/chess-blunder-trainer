from __future__ import annotations

import asyncio
import dataclasses
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from blunder_tutor.auth.types import (
    Email,
    Identity,
    IdentityId,
    PasswordHash,
    ProviderName,
    Session,
    SessionToken,
    User,
    UserId,
    Username,
)

# Sentinel yielded by ``InMemoryStorage.transaction``. Repos in
# in-memory mode receive this object as their opaque transaction
# handle and ignore it — the caller already holds the storage's
# asyncio lock, so atomicity comes from that span, not from the
# handle.
_TXN_SENTINEL = object()


def _now() -> datetime:
    return datetime.now(UTC)


def _raise_unique(constraint: str) -> None:
    """Mimic the SQLite UNIQUE-violation error message shape so
    ``AuthService._translate_integrity_error`` finds the same
    substrings (``users.username``, ``users.email``, etc.) and the
    InMemory backend behaves identically at the service layer.
    """
    raise sqlite3.IntegrityError(f"UNIQUE constraint failed: {constraint}")


def _raise_foreign_key(constraint: str) -> None:
    raise sqlite3.IntegrityError(f"FOREIGN KEY constraint failed: {constraint}")


class InMemoryStorage:
    """Test-only :class:`Storage` implementation backed by plain dicts.

    Atomicity comes from a single ``asyncio.Lock`` held by
    :meth:`transaction`; ``insert_in_transaction`` methods on the four
    repos accept the lock-held sentinel and modify the dicts directly
    without re-acquiring. This is **not** safe for production — there
    is no real isolation, no durability, and no protection against a
    coroutine that ``await`` s on something else mid-span.

    UNIQUE-violation errors are raised as :class:`sqlite3.IntegrityError`
    with the same message format that SQLite emits, so service-layer
    code that switches on the message (``_translate_integrity_error``)
    behaves identically.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._users: dict[UserId, User] = {}
        self._identities: dict[IdentityId, Identity] = {}
        self._sessions: dict[SessionToken, Session] = {}
        self._setup: dict[str, str] = {}
        self.users = _InMemoryUserRepo(self)
        self.identities = _InMemoryIdentityRepo(self)
        self.sessions = _InMemorySessionRepo(self)
        self.setup = _InMemorySetupRepo(self)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        async with self._lock:
            yield _TXN_SENTINEL


class _InMemoryUserRepo:
    def __init__(self, storage: InMemoryStorage) -> None:
        self._s = storage

    async def insert_in_transaction(
        self,
        txn: object,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
        created_at: str,
    ) -> None:
        self._check_unique(user_id=user_id, username=username, email=email)
        self._s._users[user_id] = User(
            id=user_id,
            username=username,
            email=email,
            created_at=_parse_iso(created_at),
        )

    async def insert(
        self,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
    ) -> None:
        async with self._s._lock:
            self._check_unique(user_id=user_id, username=username, email=email)
            self._s._users[user_id] = User(
                id=user_id,
                username=username,
                email=email,
                created_at=_now(),
            )

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._s._users.get(user_id)

    async def get_by_username(self, username: Username) -> User | None:
        for user in self._s._users.values():
            if user.username == username:
                return user
        return None

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._s._users.values():
            if user.email == email:
                return user
        return None

    async def count(self) -> int:
        return len(self._s._users)

    async def list_all(self) -> list[User]:
        return sorted(self._s._users.values(), key=lambda u: (u.created_at, u.id))

    async def delete(self, user_id: UserId) -> None:
        async with self._s._lock:
            self._cascade_delete(user_id)

    def _check_unique(
        self,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
    ) -> None:
        if user_id in self._s._users:
            _raise_unique("users.id")
        for user in self._s._users.values():
            if user.username == username:
                _raise_unique("users.username")
            if email is not None and user.email == email:
                _raise_unique("users.email")

    def _cascade_delete(self, user_id: UserId) -> None:
        # CASCADE: drop the user's identities + sessions before the
        # user row, mirroring SQLite's ON DELETE CASCADE on
        # ``identities.user_id`` and ``sessions.user_id``.
        for ident_id in [
            iid
            for iid, ident in self._s._identities.items()
            if ident.user_id == user_id
        ]:
            del self._s._identities[ident_id]
        for tok in [
            t for t, sess in self._s._sessions.items() if sess.user_id == user_id
        ]:
            del self._s._sessions[tok]
        self._s._users.pop(user_id, None)


class _InMemoryIdentityRepo:
    def __init__(self, storage: InMemoryStorage) -> None:
        self._s = storage

    async def insert_in_transaction(
        self,
        txn: object,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
        created_at: str,
    ) -> None:
        self._check_constraints(
            identity_id=identity_id,
            user_id=user_id,
            provider=provider,
            provider_subject=provider_subject,
        )
        self._s._identities[identity_id] = Identity(
            id=identity_id,
            user_id=user_id,
            provider=provider,
            provider_subject=provider_subject,
            credential=credential,
            created_at=_parse_iso(created_at),
        )

    async def insert(
        self,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
    ) -> None:
        async with self._s._lock:
            self._check_constraints(
                identity_id=identity_id,
                user_id=user_id,
                provider=provider,
                provider_subject=provider_subject,
            )
            self._s._identities[identity_id] = Identity(
                id=identity_id,
                user_id=user_id,
                provider=provider,
                provider_subject=provider_subject,
                credential=credential,
                created_at=_now(),
            )

    async def get_by_provider_subject(
        self, provider: ProviderName, provider_subject: str
    ) -> Identity | None:
        for ident in self._s._identities.values():
            if (
                ident.provider == provider
                and ident.provider_subject == provider_subject
            ):
                return ident
        return None

    async def list_for_user(self, user_id: UserId) -> list[Identity]:
        return sorted(
            (i for i in self._s._identities.values() if i.user_id == user_id),
            key=lambda i: (i.created_at, i.id),
        )

    async def update_credential(
        self, identity_id: IdentityId, credential: PasswordHash
    ) -> None:
        async with self._s._lock:
            existing = self._s._identities.get(identity_id)
            if existing is None:
                return
            self._s._identities[identity_id] = dataclasses.replace(
                existing, credential=credential
            )

    def _check_constraints(
        self,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
    ) -> None:
        if identity_id in self._s._identities:
            _raise_unique("identities.id")
        if user_id not in self._s._users:
            _raise_foreign_key("identities.user_id")
        for ident in self._s._identities.values():
            if (
                ident.provider == provider
                and ident.provider_subject == provider_subject
            ):
                _raise_unique("identities.provider, identities.provider_subject")


class _InMemorySessionRepo:
    def __init__(self, storage: InMemoryStorage) -> None:
        self._s = storage

    async def insert(
        self,
        *,
        token: SessionToken,
        user_id: UserId,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> None:
        async with self._s._lock:
            if token in self._s._sessions:
                _raise_unique("sessions.token")
            if user_id not in self._s._users:
                _raise_foreign_key("sessions.user_id")
            now = _now()
            self._s._sessions[token] = Session(
                token=token,
                user_id=user_id,
                created_at=now,
                expires_at=expires_at,
                last_seen_at=now,
                user_agent=user_agent,
                ip_address=ip_address,
            )

    async def get(self, token: SessionToken) -> Session | None:
        return self._s._sessions.get(token)

    async def bump_last_seen(self, token: SessionToken) -> None:
        async with self._s._lock:
            existing = self._s._sessions.get(token)
            if existing is None:
                return
            self._s._sessions[token] = dataclasses.replace(
                existing, last_seen_at=_now()
            )

    async def delete(self, token: SessionToken) -> None:
        async with self._s._lock:
            self._s._sessions.pop(token, None)

    async def delete_all_for_user(self, user_id: UserId) -> None:
        async with self._s._lock:
            for tok in [
                t for t, sess in self._s._sessions.items() if sess.user_id == user_id
            ]:
                del self._s._sessions[tok]

    async def delete_expired(self, as_of: datetime) -> int:
        async with self._s._lock:
            expired = [
                t for t, sess in self._s._sessions.items() if sess.expires_at < as_of
            ]
            for tok in expired:
                del self._s._sessions[tok]
            return len(expired)

    async def list_for_user(self, user_id: UserId) -> list[Session]:
        return sorted(
            (s for s in self._s._sessions.values() if s.user_id == user_id),
            key=lambda s: (s.created_at, s.token),
        )


class _InMemorySetupRepo:
    def __init__(self, storage: InMemoryStorage) -> None:
        self._s = storage

    async def get(self, key: str) -> str | None:
        return self._s._setup.get(key)

    async def put(self, key: str, value: str) -> None:
        async with self._s._lock:
            self._s._setup[key] = value

    async def delete(self, key: str) -> None:
        async with self._s._lock:
            self._s._setup.pop(key, None)


def _parse_iso(raw: str) -> datetime:
    """Mirror :func:`blunder_tutor.auth._time.parse_dt` so the InMemory
    backend produces the same tz-aware-UTC datetimes the SQLite backend
    hydrates from stored strings — keeps entity equality identical
    across backends in conformance tests.
    """
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed

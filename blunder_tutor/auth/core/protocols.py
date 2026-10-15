from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any, Protocol

from blunder_tutor.auth.core.errors import AuthError
from blunder_tutor.auth.core.types import (
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

# Opaque handle (`aiosqlite.Connection` for SQLite). `Any` is deliberate so protocols
# don't couple to a backend.
Transaction = Any


class UserRepo(Protocol):
    async def insert_in_transaction(
        self,
        txn: Transaction,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
        created_at: str,
    ) -> None: ...

    async def insert(
        self,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
    ) -> None: ...

    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_username(self, username: Username) -> User | None: ...
    async def get_by_email(self, email: Email) -> User | None: ...
    async def count(self) -> int: ...
    async def list_all(self) -> list[User]: ...

    async def delete(self, user_id: UserId) -> None:
        """Must cascade to identities and sessions."""
        ...


class IdentityRepo(Protocol):
    async def insert_in_transaction(
        self,
        txn: Transaction,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
        created_at: str,
    ) -> None: ...

    async def insert(
        self,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
    ) -> None: ...

    async def get_by_provider_subject(
        self, provider: ProviderName, provider_subject: str
    ) -> Identity | None: ...

    async def list_for_user(self, user_id: UserId) -> list[Identity]: ...

    async def update_credential(
        self, identity_id: IdentityId, credential: PasswordHash
    ) -> None: ...


class SessionRepo(Protocol):
    async def insert(
        self,
        *,
        token: SessionToken,
        user_id: UserId,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> None: ...

    async def get(self, token: SessionToken) -> Session | None: ...
    async def bump_last_seen(self, token: SessionToken) -> None: ...
    async def delete(self, token: SessionToken) -> None: ...
    async def delete_all_for_user(self, user_id: UserId) -> None: ...

    async def delete_expired(self, as_of: datetime) -> int: ...

    async def list_for_user(self, user_id: UserId) -> list[Session]: ...


class SetupRepo(Protocol):
    """The `*_in_transaction` variants exist because `get`/`delete` inside a transaction
    would open a separate, racy one."""

    async def get(self, key: str) -> str | None: ...
    async def put(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def get_in_transaction(self, txn: Transaction, key: str) -> str | None: ...
    async def delete_in_transaction(self, txn: Transaction, key: str) -> None: ...


class PasswordHasher(Protocol):
    """`dummy_hash` must be precomputed and cached; it keeps `CredentialsProvider`'s verify
    timing constant."""

    def hash(self, raw: str) -> PasswordHash: ...
    def verify(self, raw: str, hashed: PasswordHash) -> bool: ...
    def dummy_hash(self) -> PasswordHash: ...


class QuotaPolicy(Protocol):
    def allow_signup(self, current_count: int) -> bool: ...


class InvitePolicy(Protocol):
    async def consume(
        self,
        txn: Transaction,
        code: str | None,
        user_count: int,
    ) -> None: ...


class ErrorCodec(Protocol):
    def to_http(self, exc: AuthError) -> tuple[int, str]: ...


class Storage(Protocol):
    users: UserRepo
    identities: IdentityRepo
    sessions: SessionRepo
    setup: SetupRepo

    def transaction(self) -> AbstractAsyncContextManager[Transaction]: ...


__all__ = [
    "ErrorCodec",
    "IdentityRepo",
    "InvitePolicy",
    "PasswordHasher",
    "QuotaPolicy",
    "SessionRepo",
    "SetupRepo",
    "Storage",
    "Transaction",
    "UserRepo",
]

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import aiosqlite
from fastapi import Request, Response

from blunder_tutor.auth.types import (
    AuthError,
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


class UserRepo(Protocol):
    """Persistent store for user rows. Implementations carry their own
    storage handle (SQLite connection, in-memory dict, remote API
    client) and are constructed by the consumer; ``AuthService`` holds
    a reference and never reaches past this surface.
    """

    async def insert_in_transaction(
        self,
        conn: aiosqlite.Connection,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
        created_at: str,
    ) -> None:
        """Insert a user row inside an already-open transaction. The
        caller (``AuthService``) holds the write lock and the
        transaction span so a register / signup atomically writes both
        the user and its credentials identity.
        """
        ...

    async def insert(
        self,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
    ) -> None:
        """Insert a user row in its own transaction. Intended for tests
        and admin tooling that bypass the full register flow."""
        ...

    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_username(self, username: Username) -> User | None: ...
    async def get_by_email(self, email: Email) -> User | None: ...
    async def count(self) -> int: ...
    async def list_all(self) -> list[User]: ...

    async def delete(self, user_id: UserId) -> None:
        """Hard-delete the user row. ``ON DELETE CASCADE`` (or the
        in-memory equivalent) is expected to remove any dependent
        identities and sessions; the implementation makes the cascade
        guarantee, not the caller.
        """
        ...


class IdentityRepo(Protocol):
    """Persistent store for credential / OAuth identity rows. One user
    can own N identities (credentials + OAuth providers); the
    ``(provider, provider_subject)`` pair is unique."""

    async def insert_in_transaction(
        self,
        conn: aiosqlite.Connection,
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
    ) -> None:
        """In-place credential rotation (password reset, hash upgrade)."""
        ...


class SessionRepo(Protocol):
    """Persistent store for opaque-token sessions. Tokens are server-
    side, revocable individually or in bulk; ``last_seen_at`` is bumped
    on resolve to support idle-timeout enforcement.
    """

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

    async def delete_expired(self, as_of: datetime) -> int:
        """Bulk-delete expired sessions, returning the row count for
        diagnostics. Used by maintenance commands; ``AuthService``
        itself only deletes one session at a time on the resolve path."""
        ...

    async def list_for_user(self, user_id: UserId) -> list[Session]: ...


class SetupRepo(Protocol):
    """Tiny key/value store for one-shot bootstrap state (today: the
    first-user invite code). Operationally a SQLite table, but the
    Protocol is small enough that any backend can satisfy it.
    """

    async def get(self, key: str) -> str | None: ...
    async def put(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...


class PasswordHasher(Protocol):
    """Hash + verify primitive. Implementations may be bcrypt, argon2id,
    or a layered hasher that reads the algorithm marker on the stored
    hash and dispatches accordingly (rehash-on-login).

    ``dummy_hash`` returns a hasher-specific placeholder used by
    :class:`CredentialsProvider` to keep the verify-time wall-clock
    invariant — the implementation must precompute and cache the value
    so the constant-time path never pays the hash cost twice.
    """

    def hash(self, raw: str) -> PasswordHash: ...
    def verify(self, raw: str, hashed: PasswordHash) -> bool: ...
    def dummy_hash(self) -> PasswordHash: ...


class QuotaPolicy(Protocol):
    """Per-deploy signup-quota strategy. Called inside the signup
    transaction with the freshly observed user count; returning
    ``False`` raises :class:`UserCapReachedError` at the service layer.
    """

    def allow_signup(self, current_count: int) -> bool: ...


class InvitePolicy(Protocol):
    """First-user / always-required / never-required invite strategy.

    ``user_count`` is the snapshot from inside the signup transaction
    — a policy that gates only on first-user can return early when the
    count is non-zero. The implementation owns whatever DB calls it
    needs against the passed connection so the consume happens in the
    same atomic span as the user insert.
    """

    async def consume(
        self,
        conn: aiosqlite.Connection,
        code: str | None,
        user_count: int,
    ) -> None: ...


class RateLimiter(Protocol):
    """Per-IP rate-limit gate, callable as a FastAPI dependency.

    Matches the ``fastapi-throttle`` shape so the production limiter
    drops in directly; alternative implementations (slowapi, no-op)
    that conform to this signature are usable without service-layer
    changes.
    """

    async def __call__(self, request: Request, response: Response) -> None: ...


class ErrorCodec(Protocol):
    """Maps an :class:`AuthError` to an HTTP ``(status, detail)`` pair.
    The default codec ships blunder_tutor's stable detail slugs
    (``"username_taken"``, ``"invite_code_invalid"``, …); a consumer
    that wants i18n keys or a different status convention swaps in
    their own implementation.
    """

    def to_http(self, exc: AuthError) -> tuple[int, str]: ...


class AuthProvider(Protocol):
    """Pluggable authentication provider.

    Adding OAuth (Lichess, Google, GitHub, …) is a new class that
    satisfies this protocol — the registry on :class:`AuthService` is
    a plain dict and grows without service-layer changes.
    """

    name: ProviderName

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        """Return the matching :class:`Identity` on success, ``None`` on
        any failure mode (unknown user, wrong password, malformed
        input). Implementations must keep the wall-clock time of all
        failure paths indistinguishable from the success path so a
        timing attacker cannot enumerate users.
        """
        ...

    async def close(self) -> None:
        """Release any provider-owned resources (HTTP clients, token
        caches). Repository handles are owned by ``AuthService`` and
        are not closed here."""
        ...


__all__ = [
    "AuthProvider",
    "ErrorCodec",
    "IdentityRepo",
    "InvitePolicy",
    "PasswordHasher",
    "QuotaPolicy",
    "RateLimiter",
    "SessionRepo",
    "SetupRepo",
    "UserRepo",
]

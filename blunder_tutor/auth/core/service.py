from __future__ import annotations

import sqlite3
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, NoReturn

from blunder_tutor.auth.core._time import now_iso
from blunder_tutor.auth.core.protocols import (
    AuthProvider,
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
    """UNIQUE constraint violation → domain error. Always raises."""
    message = str(exc)
    if "users.username" in message:
        raise DuplicateUsernameError(username) from exc
    if "users.email" in message:
        raise DuplicateEmailError(email or "") from exc
    raise exc


@dataclass(frozen=True, kw_only=True)
class SessionConfig:
    """Lifetime bounds for issued sessions.

    ``kw_only=True`` because both fields are ``timedelta`` — a positional
    swap would type-check but silently invert the absolute-vs-idle
    invariant.
    """

    max_age: timedelta
    idle: timedelta


class AuthService:
    """Service layer for all auth operations.

    Owns a single :class:`Storage` aggregate (the four repos plus the
    transaction primitive). Concurrent register/login calls serialize
    correctly because the storage's transaction span is the only
    multi-statement write path; reads use the storage's read seam
    without locking.
    """

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
        # Warm the dummy hash so the first authenticate request runs in
        # the same wall-clock window as subsequent ones — the
        # constant-time invariant in :class:`CredentialsProvider`
        # depends on the dummy being precomputed.
        hasher.dummy_hash()

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
        credential = self._hasher.hash(password)
        user_id = make_user_id()
        now = now_iso()
        try:
            async with self._storage.transaction() as conn:
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

    async def signup(
        self,
        *,
        username: Username,
        password: str,
        email: Email | None = None,
        invite_code: str | None = None,
    ) -> User:
        """Atomic signup path for the HTTP surface.

        Quota enforcement and invite-consume happen inside the same
        ``BEGIN IMMEDIATE`` transaction as the ``users`` / ``identities``
        INSERTs. Without this, two concurrent POSTs to
        ``/api/auth/signup`` could both pass an API-level cap check and
        both commit, exceeding the configured quota. Single-transaction
        gating makes the cap a DB invariant instead of a best-effort
        check.

        ``register`` is the lower-level API and stays usable from tests
        that don't care about quota/invite policy.
        """
        credential = self._hasher.hash(password)
        user_id = make_user_id()
        now = now_iso()
        try:
            async with self._storage.transaction() as conn:
                # ``self._users.count()`` runs inside the open
                # ``BEGIN IMMEDIATE`` because ``UserRepository.count()``
                # uses the same shared aiosqlite connection that holds
                # the transaction; concurrent signups serialize on the
                # write lock and the cap stays a DB invariant rather
                # than a best-effort check.
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
        """Register an :class:`AuthProvider` after construction.

        The dispatch table is a plain dict keyed on ``provider.name`` —
        a consumer wiring OAuth post-boot (e.g. once a tenant configures
        SSO, or a test that swaps in a fake) calls this and the new
        provider becomes addressable through :meth:`authenticate`. Late
        registration of an already-registered name is allowed: the
        latest registration wins, matching the constructor's behaviour
        for duplicate keys in the input ``Mapping``.
        """
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
            # Session row orphaned — referential integrity should prevent
            # this, but don't trust it as a security invariant.
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
        # ``users.delete`` is a single statement — the storage backend's
        # ``ON DELETE CASCADE`` (SQLite: ``identities.user_id`` +
        # ``sessions.user_id``) removes the dependent rows atomically
        # without an explicit transaction span. SQLite atomicity here
        # depends on ``PRAGMA foreign_keys = ON`` being set on the
        # connection (see ``AuthDb.connect``); any code that opens the
        # auth DB outside ``AuthDb`` would silently break the cascade.
        # The on_after_delete hook runs AFTER the delete commits: if
        # the hook fails, the user is already logged out and cannot
        # log back in — any external resources the hook would have
        # cleaned up are a nuisance, not a data-integrity bug. Inverse
        # ordering could leave a live user with no external resources.
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
        """Rotate a user's password — hash the new value with the
        service's configured hasher, overwrite the credential row, and
        revoke every active session. Bundling the two writes is an
        OWASP V7 invariant: a credential rotation that leaves live
        tokens behind is the bug the standard exists to prevent. A
        future caller wanting to opt out of session revoke (a hash-
        upgrade-on-login path, say) should reach for the lower-level
        :meth:`IdentityRepo.update_credential` directly.
        """
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
        """Single place where a new user + their credentials identity land
        on disk. Both :meth:`register` and :meth:`signup` call this inside
        their own ``BEGIN IMMEDIATE`` transaction — adding a column to
        ``users`` or ``identities`` touches exactly one caller. Uses the
        injected repositories so the Protocol contract (instance-method
        ``insert_in_transaction``) is the single source of truth."""
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
        """Post-commit step: look up the freshly inserted user and run the
        consumer's ``on_after_register`` hook (per-user DB init, cache
        warm, audit log, etc.).

        Trade-off: if the hook fails after the auth-table commit, the
        user + identity rows already exist — the user can authenticate
        but the external resources the hook would have created are
        missing, and subsequent requests may 500. We accept this over
        (a) holding the auth write-lock for slow hook work, or (b) a
        compensating rollback that duplicates logic already handled by
        CASCADE. A future change may move hook execution to lazy-on-
        first-access to close the gap entirely.
        """
        user = await self._users.get_by_id(user_id)
        assert user is not None
        await self._on_after_register(user)
        return user

    async def _load_live_session(self, typed_token: SessionToken) -> Session | None:
        """Fetch the session and reject (with side-effecting delete) if
        it is past its absolute expiry or its idle timeout."""
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
        # Debounce ``last_seen`` writes so every authenticated request
        # doesn't serialize behind the auth DB write lock. The idle
        # timeout guarantee is unchanged: threshold is ``idle / 10``,
        # small enough that a bump happens many times per idle window
        # but large enough that a burst of requests from one client
        # coalesces into one write. At the 7-day default idle this
        # means a bump roughly every 17 hours of continuous use.
        bump_threshold = self._session_idle / 10
        if datetime.now(UTC) - session.last_seen_at >= bump_threshold:
            await self._sessions.bump_last_seen(typed_token)

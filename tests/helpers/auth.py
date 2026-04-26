from __future__ import annotations

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
    InMemoryStorage,
    InvitePolicy,
    MaxUsersQuota,
    OpenSignup,
    QuotaPolicy,
    SqliteStorage,
    Storage,
    ValidationRules,
)
from blunder_tutor.web.auth_hooks import (
    cleanup_user_dir,
    materialize_user_dir,
)


def build_test_auth_service(
    *,
    auth_db: AuthDb,
    users_dir: Path,
    session_max_age: timedelta = timedelta(days=30),
    session_idle: timedelta = timedelta(days=7),
    max_users: int = 1024,
) -> AuthService:
    """Construct an :class:`AuthService` with production-equivalent
    SQLite-backed wiring. ``max_users`` defaults high so the cap is
    effectively off; tests that exercise the cap explicitly pass a
    smaller value (or use the ``credentials_app`` fixture which boots
    via ``MAX_USERS=1`` at the env level).
    """
    storage = SqliteStorage(auth_db)
    return _build_auth_service(
        storage=storage,
        users_dir=users_dir,
        session_max_age=session_max_age,
        session_idle=session_idle,
        quota=MaxUsersQuota(max_users),
        invite_policy=HmacInvitePolicy(setup_repo=storage.setup),
    )


def build_inmemory_auth_service(
    *,
    users_dir: Path,
    session_max_age: timedelta = timedelta(days=30),
    session_idle: timedelta = timedelta(days=7),
    max_users: int = 1024,
    invite_policy: InvitePolicy | None = None,
) -> tuple[AuthService, InMemoryStorage]:
    """Construct an :class:`AuthService` against the test-only
    :class:`InMemoryStorage`. Returns the service alongside the storage
    so a test can inspect or seed the backing dicts directly.

    Defaults to :class:`OpenSignup` so callers that don't care about
    the invite gate can ignore it; pass ``invite_policy=HmacInvitePolicy(...)``
    to exercise the gated path. After TREK-59 the policy is
    storage-agnostic so InMemory now drives the same consume path as
    SQLite.
    """
    storage = InMemoryStorage()
    service = _build_auth_service(
        storage=storage,
        users_dir=users_dir,
        session_max_age=session_max_age,
        session_idle=session_idle,
        quota=MaxUsersQuota(max_users),
        invite_policy=invite_policy or OpenSignup(),
    )
    return service, storage


#: Bcrypt cost factor for the test suite. 4 is the bcrypt minimum;
#: it produces ~0.8ms hashes vs. ~160ms at the production default
#: (12), cutting ~84% of auth-suite CPU. Production `BcryptHasher`
#: instances pass no `cost` and inherit the library default.
TEST_BCRYPT_COST = 4


def _build_auth_service(
    *,
    storage: Storage,
    users_dir: Path,
    session_max_age: timedelta,
    session_idle: timedelta,
    quota: QuotaPolicy,
    invite_policy: InvitePolicy,
) -> AuthService:
    rules = ValidationRules.default()
    hasher = BcryptHasher(rules, cost=TEST_BCRYPT_COST)
    return AuthService(
        storage=storage,
        providers={
            CREDENTIALS_PROVIDER_NAME: CredentialsProvider(
                identities=storage.identities, hasher=hasher, rules=rules
            ),
        },
        hasher=hasher,
        quota=quota,
        invite_policy=invite_policy,
        on_after_register=partial(materialize_user_dir, users_dir),
        on_after_delete=partial(cleanup_user_dir, users_dir),
        session_max_age=session_max_age,
        session_idle=session_idle,
    )

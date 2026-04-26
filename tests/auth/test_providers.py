from __future__ import annotations

import time

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.hashers import BcryptHasher
from blunder_tutor.auth.providers.credentials import CredentialsProvider
from blunder_tutor.auth.repository import IdentityRepository, UserRepository
from blunder_tutor.auth.types import (
    Email,
    PasswordHash,
    Username,
    ValidationRules,
    make_identity_id,
    make_user_id,
)
from tests.helpers.auth import TEST_BCRYPT_COST


def _cheap_hash(password: str) -> PasswordHash:
    """Test-only cheap-cost hash for seeded users. Module-level
    `hash_password` from production code uses the library default cost
    (~160ms); this shim costs ~0.8ms.
    """
    return BcryptHasher(ValidationRules.default(), cost=TEST_BCRYPT_COST).hash(password)


async def _seed_user(
    auth_db: AuthDb,
    username: str,
    password: str,
    email: str | None = None,
) -> None:
    users = UserRepository(db=auth_db)
    identities = IdentityRepository(db=auth_db)
    uid = make_user_id()
    await users.insert(
        user_id=uid,
        username=Username(username),
        email=Email(email) if email else None,
    )
    await identities.insert(
        identity_id=make_identity_id(),
        user_id=uid,
        provider="credentials",
        provider_subject=username,
        credential=_cheap_hash(password),
    )


def _provider(auth_db: AuthDb, *, cost: int | None = TEST_BCRYPT_COST) -> CredentialsProvider:
    rules = ValidationRules.default()
    return CredentialsProvider(
        identities=IdentityRepository(db=auth_db),
        hasher=BcryptHasher(rules, cost=cost),
        rules=rules,
    )


class TestCredentialsProvider:
    async def test_name_is_credentials(self, auth_db: AuthDb):
        assert _provider(auth_db).name == "credentials"

    async def test_authenticate_valid(self, auth_db: AuthDb):
        await _seed_user(auth_db, "alice", "password123")
        identity = await _provider(auth_db).authenticate(
            {"username": "alice", "password": "password123"}
        )
        assert identity is not None
        assert identity.provider_subject == "alice"
        assert identity.provider == "credentials"

    async def test_authenticate_wrong_password(self, auth_db: AuthDb):
        await _seed_user(auth_db, "alice", "password123")
        assert (
            await _provider(auth_db).authenticate(
                {"username": "alice", "password": "wrong-password"}
            )
            is None
        )

    async def test_authenticate_unknown_user(self, auth_db: AuthDb):
        assert (
            await _provider(auth_db).authenticate(
                {"username": "ghost", "password": "whatever-long"}
            )
            is None
        )

    async def test_missing_fields_returns_none(self, auth_db: AuthDb):
        provider = _provider(auth_db)
        assert await provider.authenticate({}) is None
        assert await provider.authenticate({"username": "alice"}) is None
        assert await provider.authenticate({"password": "whatever"}) is None

    async def test_malformed_username_returns_none(self, auth_db: AuthDb):
        assert (
            await _provider(auth_db).authenticate(
                {"username": "has space", "password": "password123"}
            )
            is None
        )

    async def test_case_insensitive_username(self, auth_db: AuthDb):
        await _seed_user(auth_db, "alice", "password123")
        identity = await _provider(auth_db).authenticate(
            {"username": "ALICE", "password": "password123"}
        )
        assert identity is not None

    async def test_identity_without_credential_hash(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("oauthonly"), email=None)
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid,
            provider="credentials",
            provider_subject="oauthonly",
            credential=None,
        )

        assert (
            await _provider(auth_db).authenticate(
                {"username": "oauthonly", "password": "anything-long"}
            )
            is None
        )


class TestTimingEqualization:
    """Defense against username-enumeration via wall-clock timing.

    bcrypt verification takes ~100ms; if we returned immediately for
    unknown users, an attacker could enumerate valid usernames with a
    stopwatch. The provider runs a dummy verify on every miss.
    """

    async def test_unknown_user_has_bcrypt_timing(self, auth_db: AuthDb):
        # This test asserts a wall-clock invariant — both paths must run
        # one bcrypt verify. At the test-suite-default cheap cost
        # (~0.8ms) measurement noise can dominate the ratio assertion,
        # so seed AND provider here use the library-default cost.
        full_cost_hasher = BcryptHasher(ValidationRules.default(), cost=None)
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(
            user_id=uid, username=Username("alice"), email=None,
        )
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid,
            provider="credentials",
            provider_subject="alice",
            credential=full_cost_hasher.hash("password123"),
        )
        provider = _provider(auth_db, cost=None)

        # Warm any first-call jitter.
        await provider.authenticate({"username": "alice", "password": "wrong"})
        await provider.authenticate({"username": "ghost", "password": "wrong"})

        start_known = time.perf_counter()
        await provider.authenticate({"username": "alice", "password": "wrong"})
        known_elapsed = time.perf_counter() - start_known

        start_unknown = time.perf_counter()
        await provider.authenticate({"username": "ghost", "password": "wrong"})
        unknown_elapsed = time.perf_counter() - start_unknown

        # Both paths should take on the same order of magnitude (bcrypt-dominated).
        # Without the dummy hash, unknown would be ~1000x faster.
        assert unknown_elapsed > known_elapsed / 4
        assert unknown_elapsed < known_elapsed * 4

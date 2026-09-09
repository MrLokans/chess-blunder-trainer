from __future__ import annotations

from datetime import timedelta

import pytest

from blunder_tutor.auth import (
    AuthDb,
    AuthService,
    BcryptHasher,
    CredentialsProvider,
    Identity,
    IdentityRepository,
    PasswordHash,
    ProviderName,
    Username,
    ValidationRules,
)
from tests.helpers.auth import TEST_BCRYPT_COST


@pytest.fixture
def service(service_factory) -> AuthService:
    return service_factory(
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


class _RecordingIdentityRepo(IdentityRepository):
    def __init__(self, db: AuthDb) -> None:
        super().__init__(db)
        self.lookups: list[tuple[str, str]] = []

    async def get_by_provider_subject(
        self, provider: ProviderName, provider_subject: str
    ) -> Identity | None:
        self.lookups.append((provider, provider_subject))
        return await super().get_by_provider_subject(provider, provider_subject)


class _RecordingHasher(BcryptHasher):
    def __init__(self, rules: ValidationRules) -> None:
        super().__init__(rules, cost=TEST_BCRYPT_COST)
        self.verifications: list[str] = []

    def verify(self, raw: str, hashed: PasswordHash) -> bool:
        self.verifications.append(hashed[:10])
        return super().verify(raw, hashed)


def _make_recording_provider(
    auth_db: AuthDb,
) -> tuple[CredentialsProvider, _RecordingIdentityRepo, _RecordingHasher]:
    """Build a provider whose collaborators count their own calls.

    Injected through the constructor rather than monkeypatched onto a
    live provider: the counters are then part of the object graph under
    test, so no test can accidentally assert against an un-instrumented
    provider.
    """
    rules = ValidationRules.default()
    identities = _RecordingIdentityRepo(auth_db)
    hasher = _RecordingHasher(rules)
    provider = CredentialsProvider(identities=identities, hasher=hasher, rules=rules)
    return provider, identities, hasher


class TestTimingInvariants:
    """Structural guarantees that the wall-clock timing of an auth
    attempt cannot distinguish the following cases. Wall-clock timing
    tests are flaky; these assert the stronger property that every
    non-empty attempt does exactly one DB lookup and exactly one
    hasher verify call — no branch short-circuits around either.
    """

    async def test_all_failing_paths_run_one_db_query_and_one_bcrypt(
        self, service: AuthService, auth_db: AuthDb
    ):
        await service.register(username=Username("alice"), password="password123")
        provider, identities, hasher = _make_recording_provider(auth_db)

        # Case 1: malformed username (shape rejected)
        r = await provider.authenticate(
            {"username": "!!!invalid!!!", "password": "whatever123"}
        )
        assert r is None
        # Case 2: valid shape, unknown user
        r = await provider.authenticate(
            {"username": "ghost", "password": "whatever123"}
        )
        assert r is None
        # Case 3: existing user, wrong password
        r = await provider.authenticate(
            {"username": "alice", "password": "wrong-password"}
        )
        assert r is None

        assert len(identities.lookups) == 3, identities.lookups
        assert len(hasher.verifications) == 3, hasher.verifications

        # Case 4: empty creds short-circuit BEFORE DB or bcrypt — not a
        # timing leak for enumeration (attacker gains nothing by
        # learning "you sent an empty field"). Confirm the short-circuit
        # is the only exception to the invariant so the cost model is
        # explicit.
        r = await provider.authenticate({"username": "", "password": ""})
        assert r is None
        assert len(identities.lookups) == 3
        assert len(hasher.verifications) == 3

    async def test_success_path_also_runs_one_db_query_and_one_bcrypt(
        self, service: AuthService, auth_db: AuthDb
    ):
        await service.register(username=Username("alice"), password="password123")
        provider, identities, hasher = _make_recording_provider(auth_db)

        r = await provider.authenticate(
            {"username": "alice", "password": "password123"}
        )
        assert r is not None
        assert len(identities.lookups) == 1
        assert len(hasher.verifications) == 1

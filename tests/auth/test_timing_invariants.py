from __future__ import annotations

from datetime import timedelta

import pytest

from blunder_tutor.auth import (
    AuthDb,
    AuthService,
    BcryptHasher,
    CredentialsProvider,
    IdentityRepository,
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


def _make_provider(auth_db: AuthDb) -> CredentialsProvider:
    rules = ValidationRules.default()
    return CredentialsProvider(
        identities=IdentityRepository(db=auth_db),
        hasher=BcryptHasher(rules, cost=TEST_BCRYPT_COST),
        rules=rules,
    )


class TestTimingInvariants:
    """Structural guarantees that the wall-clock timing of an auth
    attempt cannot distinguish the following cases. Wall-clock timing
    tests are flaky; these assert the stronger property that every
    non-empty attempt does exactly one DB lookup and exactly one
    hasher verify call — no branch short-circuits around either.
    """

    async def test_all_failing_paths_run_one_db_query_and_one_bcrypt(
        self, service: AuthService, auth_db: AuthDb, monkeypatch
    ):
        await service.register(username=Username("alice"), password="password123")

        provider = _make_provider(auth_db)

        db_calls: list[tuple[str, str]] = []
        orig_lookup = provider._identities.get_by_provider_subject

        async def spy_lookup(provider_name, subject):
            db_calls.append((provider_name, subject))
            return await orig_lookup(provider_name, subject)

        monkeypatch.setattr(provider._identities, "get_by_provider_subject", spy_lookup)

        verify_calls: list[str] = []
        orig_verify = provider._hasher.verify

        def spy_verify(raw, hashed):
            verify_calls.append(hashed[:10])
            return orig_verify(raw, hashed)

        monkeypatch.setattr(provider._hasher, "verify", spy_verify)

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

        assert len(db_calls) == 3, db_calls
        assert len(verify_calls) == 3, verify_calls

        # Case 4: empty creds short-circuit BEFORE DB or bcrypt — not a
        # timing leak for enumeration (attacker gains nothing by
        # learning "you sent an empty field"). Confirm the short-circuit
        # is the only exception to the invariant so the cost model is
        # explicit.
        r = await provider.authenticate({"username": "", "password": ""})
        assert r is None
        assert len(db_calls) == 3
        assert len(verify_calls) == 3

    async def test_success_path_also_runs_one_db_query_and_one_bcrypt(
        self, service: AuthService, auth_db: AuthDb, monkeypatch
    ):
        await service.register(username=Username("alice"), password="password123")

        provider = _make_provider(auth_db)

        db_calls: list[tuple[str, str]] = []
        orig_lookup = provider._identities.get_by_provider_subject

        async def spy_lookup(provider_name, subject):
            db_calls.append((provider_name, subject))
            return await orig_lookup(provider_name, subject)

        monkeypatch.setattr(provider._identities, "get_by_provider_subject", spy_lookup)

        verify_calls: list[str] = []
        orig_verify = provider._hasher.verify

        def spy_verify(raw, hashed):
            verify_calls.append(hashed[:10])
            return orig_verify(raw, hashed)

        monkeypatch.setattr(provider._hasher, "verify", spy_verify)

        r = await provider.authenticate(
            {"username": "alice", "password": "password123"}
        )
        assert r is not None
        assert len(db_calls) == 1
        assert len(verify_calls) == 1

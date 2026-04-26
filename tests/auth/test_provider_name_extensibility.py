"""Tests for the ``ProviderName`` extensibility contract (TREK-55 / P3.3).

Pin the runtime shape that lets a library consumer mint provider
names for backends the auth core has never heard of (``"github"``,
``"azure-ad"``, ``"saml-corp"``…) without forking the
``Literal["credentials", "lichess", "google"]`` enumeration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from blunder_tutor.auth.types import (
    Identity,
    ProviderName,
    Username,
    make_identity_id,
)
from tests.helpers.auth import build_inmemory_auth_service


class _RecordingProvider:
    """Stub provider that returns a pre-seeded identity on the first
    successful credential match. Used to drive the AuthService dispatch
    table without touching any real auth backend.
    """

    def __init__(self, *, name: str, identity: Identity) -> None:
        self.name = ProviderName(name)
        self._identity = identity
        self.calls: list[dict[str, str]] = []

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        self.calls.append(credentials)
        if credentials.get("token") == "ok":
            return self._identity
        return None

    async def close(self) -> None:
        pass


class TestProviderNameType:
    def test_accepts_arbitrary_string(self):
        # Pre-TREK-55 this raised ``TypeError: Cannot instantiate
        # typing.Literal``. The NewType form lets a consumer mint
        # provider names for backends the auth core never enumerated.
        name = ProviderName("github")
        assert name == "github"
        assert isinstance(name, str)

    def test_minted_name_is_truthy_and_hashable(self):
        # Provider names are used as dict keys in the AuthService
        # registry; pin the contract so a future refactor that wraps
        # ProviderName in a non-hashable container fails loudly here
        # rather than at request time.
        name = ProviderName("custom")
        assert {name: "value"}[name] == "value"


class TestAuthServiceAcceptsArbitraryProviderNames:
    @pytest.fixture
    async def wired(self, tmp_path: Path):
        service, storage = build_inmemory_auth_service(users_dir=tmp_path / "users")
        # Seed a user the custom provider will resolve to.
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        identity = Identity(
            id=make_identity_id(),
            user_id=user.id,
            provider=ProviderName("github"),
            provider_subject="alice@github",
            credential=None,
            created_at=datetime.now(UTC),
        )
        return service, storage, identity, user

    async def test_dispatches_to_custom_named_provider(self, wired):
        service, _storage, identity, user = wired
        provider = _RecordingProvider(name="github", identity=identity)
        service.register_provider(provider)

        result = await service.authenticate(provider.name, {"token": "ok"})
        assert result is not None
        assert result.id == user.id
        assert provider.calls == [{"token": "ok"}]

    async def test_distinct_custom_names_dispatch_independently(self, wired):
        # Two providers with arbitrary, non-enumerated names must each
        # be reachable through their own key — proves the registry is
        # genuinely keyed on the consumer-supplied name and that the
        # NewType form imposes no closed enumeration on it.
        service, _storage, identity, _user = wired
        github = _RecordingProvider(name="github", identity=identity)
        azure = _RecordingProvider(name="azure-ad", identity=identity)
        service.register_provider(github)
        service.register_provider(azure)

        await service.authenticate(github.name, {"token": "ok"})
        await service.authenticate(azure.name, {"token": "wrong"})

        assert github.calls == [{"token": "ok"}]
        assert azure.calls == [{"token": "wrong"}]

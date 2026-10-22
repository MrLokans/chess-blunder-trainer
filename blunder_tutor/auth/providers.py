from __future__ import annotations

import asyncio
from typing import Protocol

from blunder_tutor.auth.core.protocols import IdentityRepo, PasswordHasher
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    AuthError,
    CorruptCredentialError,
    Identity,
    PasswordHash,
    ProviderName,
    Username,
    ValidationRules,
)


class AuthProvider(Protocol):
    name: ProviderName

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None: ...

    async def close(self) -> None: ...


class CredentialsProvider:
    """Constant-time credentials auth.

    Every non-empty attempt does one identities SELECT and one `verify` (against the
    real hash or `dummy_hash`) without short-circuiting, so timing cannot tell apart a
    malformed username, an unknown user, an OAuth-only user or a wrong password."""

    name: ProviderName = CREDENTIALS_PROVIDER_NAME

    def __init__(
        self,
        *,
        identities: IdentityRepo,
        hasher: PasswordHasher,
        rules: ValidationRules,
    ) -> None:
        self._identities = identities
        self._hasher = hasher
        self._rules = rules

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        raw_username = credentials.get("username", "")
        raw_password = credentials.get("password", "")
        if not raw_username or not raw_password:
            return None

        try:
            username_lookup: Username = self._rules.make_username(raw_username)
        except AuthError:
            # Unmatchable sentinel: never a real `provider_subject`, so the SELECT
            # misses but costs the same DB time.
            username_lookup = Username("")

        identity = await self._identities.get_by_provider_subject(
            self.name, username_lookup
        )

        # `verify` runs unconditionally so the cost doesn't depend on hit vs miss.
        hash_to_verify: PasswordHash = (
            identity.credential
            if identity is not None and identity.credential is not None
            else self._hasher.dummy_hash()
        )

        try:
            # bcrypt is ~250ms of CPU; off the loop so a login flood can't stall it.
            verified = await asyncio.to_thread(
                self._hasher.verify, raw_password, hash_to_verify
            )
        except CorruptCredentialError:
            # Corruption counts as an auth miss here; a 500 would leak it.
            verified = False

        if identity is None or identity.credential is None or not verified:
            return None
        return identity

    async def close(self) -> None:
        pass

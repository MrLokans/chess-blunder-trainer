from __future__ import annotations

from contextlib import suppress

from blunder_tutor.auth.repository import IdentityRepository
from blunder_tutor.auth.types import (
    AuthError,
    CorruptCredentialError,
    Identity,
    PasswordHash,
    ProviderName,
    hash_password,
    make_username,
    verify_password,
)

# Pre-computed bcrypt hash of a placeholder password. `authenticate` runs
# a verify against this on every "user not found" and "identity missing
# credential" path so the wall-clock time of an auth attempt is the same
# whether the username is valid or not. Without this, an attacker can
# enumerate valid usernames with a stopwatch.
_DUMMY_HASH: PasswordHash = hash_password("dummy-password-for-timing-equalization")


class CredentialsProvider:
    name: ProviderName = "credentials"

    def __init__(self, identities: IdentityRepository) -> None:
        self._identities = identities

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        raw_username = credentials.get("username")
        raw_password = credentials.get("password")
        if not raw_username or not raw_password:
            return None
        try:
            username = make_username(raw_username)
        except AuthError:
            # Malformed inputs are auth misses, not exceptions — and we
            # still consume bcrypt time so that "bad shape" is not
            # distinguishable from "unknown user" via wall clock.
            self._consume_dummy_time(raw_password)
            return None

        identity = await self._identities.get_by_provider_subject(
            "credentials", username
        )
        if identity is None or identity.credential is None:
            self._consume_dummy_time(raw_password)
            return None

        try:
            if not verify_password(raw_password, identity.credential):
                return None
        except CorruptCredentialError:
            # Treat DB corruption as an auth miss for the user-facing path;
            # the exception has already been raised in logs via the raise
            # chain in verify_password, and we don't want to leak via a
            # 500 response.
            return None
        return identity

    async def close(self) -> None:
        # Identity repo is owned by AuthService — provider does not close it.
        pass

    @staticmethod
    def _consume_dummy_time(raw_password: str) -> None:
        # Dummy hash is well-formed; CorruptCredentialError is unreachable
        # but we suppress defensively — the timing-equalizer must never
        # become a new exception source.
        with suppress(CorruptCredentialError):
            verify_password(raw_password, _DUMMY_HASH)

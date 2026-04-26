from __future__ import annotations

from blunder_tutor.auth.protocols import IdentityRepo, PasswordHasher
from blunder_tutor.auth.types import (
    CREDENTIALS_PROVIDER_NAME,
    AuthError,
    CorruptCredentialError,
    Identity,
    PasswordHash,
    ProviderName,
    Username,
    ValidationRules,
)


class CredentialsProvider:
    """Credentials auth provider with constant-time authentication path.

    Every non-empty authentication attempt takes the same wall-clock
    shape:

    1. One ``identities`` SELECT (empty lookup when the username is
       malformed — returns no row but consumes the same DB time).
    2. One :meth:`PasswordHasher.verify` call against either the real
       hash (if found) or the hasher's :meth:`dummy_hash` (if not).

    The Boolean result is the logical AND of "row found with a credential"
    and "verify returned True". Neither branch short-circuits around the
    DB lookup or the bcrypt verify, so a timing attacker cannot
    distinguish:

    * malformed username (rejected by ``make_username``),
    * valid-shape username that doesn't exist,
    * OAuth-only identity with no credential,
    * existing credentials user with a wrong password.
    """

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
            # Unmatchable sentinel. The UNIQUE constraint on
            # ``identities.provider_subject`` plus the ``make_username``
            # 3–32-char rule guarantees no real row has an empty
            # ``provider_subject``, so this SELECT is always a miss —
            # but it spends the same DB time as a real lookup.
            username_lookup = Username("")

        identity = await self._identities.get_by_provider_subject(
            self.name, username_lookup
        )

        # Pick the hash to verify: real if found, dummy otherwise.
        # ``verify`` runs unconditionally on every non-empty attempt
        # so the bcrypt cost is independent of DB-miss vs. DB-hit.
        hash_to_verify: PasswordHash = (
            identity.credential
            if identity is not None and identity.credential is not None
            else self._hasher.dummy_hash()
        )

        try:
            verified = self._hasher.verify(raw_password, hash_to_verify)
        except CorruptCredentialError:
            # Treat DB corruption as an auth miss for the user-facing
            # path; the exception has already been raised in logs via
            # the hasher's raise chain, and we don't want to leak via
            # a 500 response.
            verified = False

        if identity is None or identity.credential is None or not verified:
            return None
        return identity

    async def close(self) -> None:
        # Identity repo is owned by AuthService — provider does not close it.
        pass

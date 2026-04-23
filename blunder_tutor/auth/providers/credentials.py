from __future__ import annotations

from blunder_tutor.auth.repository import IdentityRepository
from blunder_tutor.auth.types import (
    AuthError,
    CorruptCredentialError,
    Identity,
    PasswordHash,
    ProviderName,
    Username,
    hash_password,
    make_username,
    verify_password,
)

# Pre-computed bcrypt hash of a placeholder password. `authenticate` runs
# a verify against this on every "user not found" / "credential missing"
# path so the wall-clock time of an auth attempt is the same whether the
# username is valid or not. Without this, an attacker can enumerate
# valid usernames with a stopwatch.
_DUMMY_HASH: PasswordHash = hash_password("dummy-password-for-timing-equalization")


class CredentialsProvider:
    """Credentials auth provider with constant-time authentication path.

    Every non-empty authentication attempt takes the same wall-clock
    shape:

    1. One ``identities`` SELECT (empty lookup when the username is
       malformed — returns no row but consumes the same DB time).
    2. One ``verify_password`` call against either the real hash (if
       found) or :data:`_DUMMY_HASH` (if not).

    The Boolean result is the logical AND of "row found with a credential"
    and "verify_password returned True". Neither branch short-circuits
    around the DB lookup or the bcrypt verify, so a timing attacker
    cannot distinguish:

    * malformed username (rejected by ``make_username``),
    * valid-shape username that doesn't exist,
    * OAuth-only identity with no credential,
    * existing credentials user with a wrong password.
    """

    name: ProviderName = "credentials"

    def __init__(self, identities: IdentityRepository) -> None:
        self._identities = identities

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        raw_username = credentials.get("username", "")
        raw_password = credentials.get("password", "")
        if not raw_username or not raw_password:
            return None

        try:
            username_lookup: Username = make_username(raw_username)
        except AuthError:
            # Unmatchable sentinel. The UNIQUE constraint on
            # ``identities.provider_subject`` plus the ``make_username``
            # 3–32-char rule guarantees no real row has an empty
            # ``provider_subject``, so this SELECT is always a miss —
            # but it spends the same DB time as a real lookup.
            username_lookup = Username("")

        identity = await self._identities.get_by_provider_subject(
            "credentials", username_lookup
        )

        # Pick the hash to verify: real if found, dummy otherwise.
        # verify_password runs unconditionally on every non-empty attempt
        # so the bcrypt cost is independent of DB-miss vs. DB-hit.
        hash_to_verify: PasswordHash = (
            identity.credential
            if identity is not None and identity.credential is not None
            else _DUMMY_HASH
        )

        try:
            verified = verify_password(raw_password, hash_to_verify)
        except CorruptCredentialError:
            # Treat DB corruption as an auth miss for the user-facing
            # path; the exception has already been raised in logs via
            # verify_password's raise chain, and we don't want to leak
            # via a 500 response.
            verified = False

        if identity is None or identity.credential is None or not verified:
            return None
        return identity

    async def close(self) -> None:
        # Identity repo is owned by AuthService — provider does not close it.
        pass

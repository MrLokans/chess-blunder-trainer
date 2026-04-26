from __future__ import annotations

import hmac

from blunder_tutor.auth.core.errors import InvalidInviteCodeError
from blunder_tutor.auth.core.protocols import SetupRepo, Transaction

# SetupRepo key under which the first-user invite code is stored.
# Read by :class:`HmacInvitePolicy.consume`, written by
# :func:`blunder_tutor.auth.cli.admin.regenerate_invite` and the
# bootstrap path in ``blunder_tutor/web/app.py:_bootstrap_auth``.
# A typo in any of those would silently break the invite flow across
# the deploy boundary, so the literal lives in exactly one place.
INVITE_CODE_SETUP_KEY = "invite_code"


class MaxUsersQuota:
    """Cap signups at a fixed user count. Set ``max_users=1`` for
    single-user self-hosted, larger for shared deploys.
    """

    def __init__(self, max_users: int) -> None:
        self._max_users = max_users

    def allow_signup(self, current_count: int) -> bool:
        return current_count < self._max_users


class NoQuota:
    """No signup cap — every signup is permitted regardless of the
    current user count. Use for SaaS / public registration."""

    def allow_signup(self, current_count: int) -> bool:
        return True


class HmacInvitePolicy:
    """First-user invite required; subsequent signups don't need one.

    Constant-time match against a stored row in the auth ``setup`` key/
    value store; accept deletes the row (single-use). The HMAC suffix
    on the invite code is verified at *issue* time by
    ``generate_invite_code``; re-verifying at consume time was decided
    against (TREK-19/25) — any code that byte-matches the stored value
    was signed by us by construction, and re-verification creates a
    silent failure path after SECRET_KEY rotation.

    The policy reads/writes through a :class:`SetupRepo`, so it is
    storage-agnostic — SQLite and any future backend that satisfies
    the protocol all run the same consume path.
    """

    def __init__(self, setup_repo: SetupRepo) -> None:
        self._setup_repo = setup_repo

    async def consume(
        self,
        txn: Transaction,
        code: str | None,
        user_count: int,
    ) -> None:
        if user_count > 0:
            return
        if not code:
            raise InvalidInviteCodeError("missing")
        stored = await self._setup_repo.get_in_transaction(txn, INVITE_CODE_SETUP_KEY)
        if stored is None:
            raise InvalidInviteCodeError("not_issued")
        if not hmac.compare_digest(code, stored):
            raise InvalidInviteCodeError("rotated")
        await self._setup_repo.delete_in_transaction(txn, INVITE_CODE_SETUP_KEY)


class OpenSignup:
    """No invite ever required. Useful for public SaaS registration or
    test scenarios where the first-user gate is irrelevant."""

    async def consume(
        self,
        txn: Transaction,
        code: str | None,
        user_count: int,
    ) -> None:
        return

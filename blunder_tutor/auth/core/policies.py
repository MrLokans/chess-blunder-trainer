from __future__ import annotations

import hmac

from blunder_tutor.auth.core.errors import InvalidInviteCodeError
from blunder_tutor.auth.core.protocols import SetupRepo, Transaction

# Single literal shared by the policy, `regenerate_invite` and bootstrap; a typo would
# silently break the invite flow.
INVITE_CODE_SETUP_KEY = "invite_code"


class MaxUsersQuota:
    def __init__(self, max_users: int) -> None:
        self._max_users = max_users

    def allow_signup(self, current_count: int) -> bool:
        return current_count < self._max_users


class NoQuota:
    def allow_signup(self, current_count: int) -> bool:
        return True


class HmacInvitePolicy:
    """Consumes by constant-time match against the code in the setup store (single use).

    The HMAC is verified only at issue time: a byte-match proves we signed it, and
    re-verifying would fail after SECRET_KEY rotation."""

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
    async def consume(
        self,
        txn: Transaction,
        code: str | None,
        user_count: int,
    ) -> None: ...

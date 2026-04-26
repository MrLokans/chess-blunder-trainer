from __future__ import annotations

import hmac

import aiosqlite

from blunder_tutor.auth.types import InvalidInviteCodeError


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

    Constant-time match against a stored row in the auth ``setup`` table;
    accept deletes the row (single-use). The HMAC suffix on the invite
    code is verified at *issue* time by ``generate_invite_code``;
    re-verifying at consume time was decided against (TREK-19/25) — any
    code that byte-matches the stored value was signed by us by
    construction, and re-verification creates a silent failure path
    after SECRET_KEY rotation.

    **Storage coupling**: the consume path issues raw SQL on the
    transaction handle, so this policy currently requires an
    aiosqlite-shaped ``txn`` (the SQLite backend's transaction conn).
    Test-doubles / non-SQL backends should wire :class:`OpenSignup`
    until TREK-59 routes the invite read/delete through ``SetupRepo``.
    The ``hasattr`` guard below makes the failure mode loud instead of
    a duck-typed ``AttributeError`` deeper in the call stack.
    """

    async def consume(
        self,
        conn: aiosqlite.Connection,
        code: str | None,
        user_count: int,
    ) -> None:
        if user_count > 0:
            return
        if not hasattr(conn, "execute"):
            raise NotImplementedError(
                "HmacInvitePolicy requires an aiosqlite-shaped transaction "
                "handle (issues raw SQL on `conn.execute`). Wire OpenSignup "
                "for in-memory / non-SQL backends until TREK-59 lands."
            )
        if not code:
            raise InvalidInviteCodeError("missing")
        async with conn.execute(
            "SELECT value FROM setup WHERE key = 'invite_code'"
        ) as cur:
            stored_row = await cur.fetchone()
        if stored_row is None:
            raise InvalidInviteCodeError("not_issued")
        stored = stored_row[0]
        if not hmac.compare_digest(code, stored):
            raise InvalidInviteCodeError("rotated")
        await conn.execute("DELETE FROM setup WHERE key = 'invite_code'")


class OpenSignup:
    """No invite ever required. Useful for public SaaS registration or
    test scenarios where the first-user gate is irrelevant."""

    async def consume(
        self,
        conn: aiosqlite.Connection,
        code: str | None,
        user_count: int,
    ) -> None:
        return

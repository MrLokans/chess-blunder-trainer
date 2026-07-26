from __future__ import annotations

from datetime import datetime

import aiosqlite

from blunder_tutor.auth import AuthDb, UserId
from blunder_tutor.billing.types import (
    BillingPlan,
    StripeCustomerId,
    StripeSubscriptionId,
    Subscription,
    SubscriptionStatus,
)
from blunder_tutor.utils.time import now_iso, parse_dt

_SELECT = """
    SELECT user_id, stripe_customer_id, stripe_subscription_id, status,
           plan, trial_ends_at, current_period_end, created_at, updated_at
    FROM subscriptions
"""


def _row_to_subscription(row: aiosqlite.Row) -> Subscription:
    return Subscription(
        user_id=UserId(row[0]),
        stripe_customer_id=StripeCustomerId(row[1]) if row[1] else None,
        stripe_subscription_id=StripeSubscriptionId(row[2]) if row[2] else None,
        status=SubscriptionStatus(row[3]),
        plan=BillingPlan(row[4]) if row[4] else None,
        trial_ends_at=parse_dt(row[5]),
        current_period_end=parse_dt(row[6]) if row[6] else None,
        created_at=parse_dt(row[7]),
        updated_at=parse_dt(row[8]),
    )


class SubscriptionRepository:
    def __init__(self, db: AuthDb) -> None:
        self._db = db

    async def get(self, user_id: UserId) -> Subscription | None:
        return await self._fetch_one("WHERE user_id = ?", (user_id,))

    async def find_by_customer(self, customer_id: str) -> Subscription | None:
        return await self._fetch_one("WHERE stripe_customer_id = ?", (customer_id,))

    async def start_trial(
        self, *, user_id: UserId, trial_ends_at: datetime, node_id: str
    ) -> None:
        now = now_iso()
        async with self._db.write() as conn:
            await conn.execute(
                """
                INSERT OR IGNORE INTO subscriptions
                    (user_id, status, trial_ends_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    SubscriptionStatus.TRIALING.value,
                    trial_ends_at.isoformat(),
                    now,
                    now,
                ),
            )
            await conn.execute(
                "INSERT OR IGNORE INTO user_nodes (user_id, node_id) VALUES (?, ?)",
                (user_id, node_id),
            )

    async def apply_stripe_update(
        self,
        *,
        user_id: UserId,
        customer_id: str,
        subscription_id: str,
        status: SubscriptionStatus,
        plan: BillingPlan | None,
        current_period_end: datetime | None,
    ) -> None:
        async with self._db.write() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET stripe_customer_id = ?, stripe_subscription_id = ?,
                    status = ?, plan = ?, current_period_end = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    customer_id,
                    subscription_id,
                    status.value,
                    plan.value if plan else None,
                    current_period_end.isoformat() if current_period_end else None,
                    now_iso(),
                    user_id,
                ),
            )

    async def event_processed(self, event_id: str) -> bool:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT 1 FROM webhook_events WHERE event_id = ?", (event_id,)
        ) as cur:
            return await cur.fetchone() is not None

    async def record_event(self, event_id: str) -> bool:
        async with self._db.write() as conn:
            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO webhook_events (event_id, received_at)
                VALUES (?, ?)
                """,
                (event_id, now_iso()),
            )
            return cursor.rowcount == 1

    async def get_node(self, user_id: UserId) -> str | None:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT node_id FROM user_nodes WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def delete_user(self, user_id: UserId) -> None:
        async with self._db.write() as conn:
            await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = ?", (user_id,)
            )
            await conn.execute("DELETE FROM user_nodes WHERE user_id = ?", (user_id,))

    async def _fetch_one(self, where: str, params: tuple) -> Subscription | None:
        conn = await self._db.conn()
        async with conn.execute(f"{_SELECT} {where}", params) as cur:  # noqa: S608
            row = await cur.fetchone()
        return _row_to_subscription(row) if row else None

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

from blunder_tutor.auth import UserId

StripeCustomerId = NewType("StripeCustomerId", str)
StripeSubscriptionId = NewType("StripeSubscriptionId", str)
NodeId = NewType("NodeId", str)


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class BillingPlan(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


@dataclass(frozen=True, slots=True, kw_only=True)
class Subscription:
    user_id: UserId
    stripe_customer_id: StripeCustomerId | None
    stripe_subscription_id: StripeSubscriptionId | None
    status: SubscriptionStatus
    plan: BillingPlan | None
    trial_ends_at: datetime
    current_period_end: datetime | None
    created_at: datetime
    updated_at: datetime

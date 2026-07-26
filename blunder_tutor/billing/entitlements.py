from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from blunder_tutor.billing.types import Subscription, SubscriptionStatus

CLOUD_GRANTS: frozenset[str] = frozenset(("cloud.autosync", "cloud.email_nudges"))

_SECONDS_PER_DAY = 86400


@dataclass(frozen=True, slots=True, kw_only=True)
class Entitlements:
    plan_status: str
    read_only: bool
    grants: frozenset[str]
    trial_ends_at: datetime | None
    trial_days_left: int = 0


_LAPSED = Entitlements(
    plan_status="lapsed",
    read_only=True,
    grants=frozenset(),
    trial_ends_at=None,
)


def _days_between(later: datetime, now: datetime) -> int:
    return max(0, int((later - now).total_seconds() // _SECONDS_PER_DAY))


def _full(
    plan_status: str,
    trial_ends_at: datetime | None = None,
    trial_days_left: int = 0,
) -> Entitlements:
    return Entitlements(
        plan_status=plan_status,
        read_only=False,
        grants=CLOUD_GRANTS,
        trial_ends_at=trial_ends_at,
        trial_days_left=trial_days_left,
    )


def _resolve_trialing(sub: Subscription, now: datetime) -> Entitlements:
    if now > sub.trial_ends_at:
        return _LAPSED
    return _full(
        "trialing",
        trial_ends_at=sub.trial_ends_at,
        trial_days_left=_days_between(sub.trial_ends_at, now),
    )


def _resolve_canceled(sub: Subscription, now: datetime) -> Entitlements:
    # A canceled subscription retains access until the paid period ends.
    if sub.current_period_end is not None and now <= sub.current_period_end:
        return _full("active")
    return _LAPSED


_RESOLVERS = MappingProxyType(
    {
        SubscriptionStatus.ACTIVE: lambda sub, now: _full("active"),
        SubscriptionStatus.PAST_DUE: lambda sub, now: _full("past_due"),
        SubscriptionStatus.TRIALING: _resolve_trialing,
        SubscriptionStatus.CANCELED: _resolve_canceled,
    }
)


def resolve_entitlements(sub: Subscription | None, now: datetime) -> Entitlements:
    if sub is None:
        return _LAPSED
    return _RESOLVERS[sub.status](sub, now)

from datetime import UTC, datetime, timedelta

import pytest

from blunder_tutor.auth import UserId
from blunder_tutor.billing.entitlements import CLOUD_GRANTS, resolve_entitlements
from blunder_tutor.billing.types import Subscription, SubscriptionStatus

NOW = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)


def make_sub(**overrides) -> Subscription:
    base = {
        "user_id": UserId("a" * 32),
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "status": SubscriptionStatus.TRIALING,
        "plan": None,
        "trial_ends_at": NOW + timedelta(days=7),
        "current_period_end": None,
        "created_at": NOW - timedelta(days=7),
        "updated_at": NOW - timedelta(days=7),
    }
    return Subscription(**{**base, **overrides})


class TestResolveEntitlements:
    @pytest.mark.parametrize(
        ("sub", "expected_status", "expected_read_only"),
        [
            (make_sub(), "trialing", False),
            (make_sub(trial_ends_at=NOW - timedelta(days=1)), "lapsed", True),
            (make_sub(status=SubscriptionStatus.ACTIVE), "active", False),
            (make_sub(status=SubscriptionStatus.PAST_DUE), "past_due", False),
            (
                make_sub(
                    status=SubscriptionStatus.CANCELED,
                    current_period_end=NOW + timedelta(days=10),
                ),
                "active",
                False,
            ),
            (
                make_sub(
                    status=SubscriptionStatus.CANCELED,
                    current_period_end=NOW - timedelta(days=1),
                ),
                "lapsed",
                True,
            ),
            (None, "lapsed", True),
        ],
    )
    def test_status_matrix(self, sub, expected_status, expected_read_only):
        ent = resolve_entitlements(sub, NOW)
        assert ent.plan_status == expected_status
        assert ent.read_only is expected_read_only

    def test_full_access_carries_all_grants(self):
        assert resolve_entitlements(make_sub(), NOW).grants == CLOUD_GRANTS

    def test_lapsed_has_no_grants(self):
        assert resolve_entitlements(None, NOW).grants == frozenset()

    def test_trial_days_left(self):
        assert resolve_entitlements(make_sub(), NOW).trial_days_left == 7
        assert resolve_entitlements(None, NOW).trial_days_left == 0

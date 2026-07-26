from datetime import UTC, datetime, timedelta

from blunder_tutor.auth import UserId
from blunder_tutor.billing.types import BillingPlan, SubscriptionStatus

ALICE = UserId("a" * 32)
TRIAL_END = datetime(2026, 8, 1, tzinfo=UTC)


class TestStartTrial:
    async def test_creates_trialing_row_and_node(self, repo):
        await repo.start_trial(user_id=ALICE, trial_ends_at=TRIAL_END, node_id="node-1")
        sub = await repo.get(ALICE)
        assert sub is not None
        assert sub.status is SubscriptionStatus.TRIALING
        assert sub.trial_ends_at == TRIAL_END
        assert await repo.get_node(ALICE) == "node-1"

    async def test_is_idempotent(self, repo):
        await repo.start_trial(user_id=ALICE, trial_ends_at=TRIAL_END, node_id="node-1")
        later = TRIAL_END + timedelta(days=30)
        await repo.start_trial(user_id=ALICE, trial_ends_at=later, node_id="node-2")
        sub = await repo.get(ALICE)
        assert sub.trial_ends_at == TRIAL_END
        assert await repo.get_node(ALICE) == "node-1"


class TestApplyStripeUpdate:
    async def test_activates_and_finds_by_customer(self, repo):
        await repo.start_trial(user_id=ALICE, trial_ends_at=TRIAL_END, node_id="node-1")
        period_end = datetime(2026, 9, 1, tzinfo=UTC)
        await repo.apply_stripe_update(
            user_id=ALICE,
            customer_id="cus_1",
            subscription_id="sub_1",
            status=SubscriptionStatus.ACTIVE,
            plan=BillingPlan.MONTHLY,
            current_period_end=period_end,
        )
        sub = await repo.find_by_customer("cus_1")
        assert sub is not None
        assert sub.user_id == ALICE
        assert sub.status is SubscriptionStatus.ACTIVE
        assert sub.plan is BillingPlan.MONTHLY
        assert sub.current_period_end == period_end


class TestRecordEvent:
    async def test_first_time_true_then_false(self, repo):
        assert await repo.record_event("evt_1") is True
        assert await repo.record_event("evt_1") is False


class TestDeleteUser:
    async def test_removes_all_rows(self, repo):
        await repo.start_trial(user_id=ALICE, trial_ends_at=TRIAL_END, node_id="node-1")
        await repo.delete_user(ALICE)
        assert await repo.get(ALICE) is None
        assert await repo.get_node(ALICE) is None

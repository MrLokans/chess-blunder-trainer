import json
from datetime import UTC, datetime

import pytest

from blunder_tutor.auth import UserId
from blunder_tutor.billing.service import BillingService, WebhookPayloadError
from blunder_tutor.billing.stripe_gateway import SubscriptionState
from blunder_tutor.billing.types import BillingPlan, SubscriptionStatus
from blunder_tutor.web.config import BillingConfig
from tests.billing.fakes import FakeStripeGateway

ALICE = UserId("a" * 32)

CONFIG = BillingConfig(
    cloud_mode=True,
    stripe_secret_key="sk_test_x",
    stripe_webhook_secret="whsec_x",
    stripe_price_monthly="price_m",
    stripe_price_annual="price_a",
    public_base_url="https://cloud.example.com",
)

PERIOD_END = datetime(2026, 9, 1, tzinfo=UTC)


def _webhook(event_id: str, event_type: str, data: dict) -> bytes:
    return json.dumps(
        {"id": event_id, "type": event_type, "data": {"object": data}}
    ).encode()


def _checkout_completed(event_id: str = "evt_checkout") -> bytes:
    return _webhook(
        event_id,
        "checkout.session.completed",
        {"client_reference_id": ALICE, "customer": "cus_1", "subscription": "sub_1"},
    )


def _sub_updated(event_id: str, **data_overrides) -> bytes:
    data = {"id": "sub_1", "customer": "cus_1", "status": "active", **data_overrides}
    return _webhook(event_id, "customer.subscription.updated", data)


def _live_state(**overrides) -> SubscriptionState:
    base = {
        "subscription_id": "sub_1",
        "customer_id": "cus_1",
        "status": "active",
        "price_id": "price_m",
        "current_period_end": PERIOD_END,
    }
    return SubscriptionState(**{**base, **overrides})


@pytest.fixture
def gateway() -> FakeStripeGateway:
    fake = FakeStripeGateway()
    fake.subscriptions["sub_1"] = _live_state()
    return fake


@pytest.fixture
def service(repo, gateway) -> BillingService:
    return BillingService(repo=repo, gateway=gateway, config=CONFIG)


class TestOutOfOrderDelivery:
    async def test_updated_before_checkout_self_heals(self, service, repo):
        await service.get_entitlements(ALICE)
        # subscription.updated arrives first: customer unknown, event is
        # absorbed without effect...
        await service.handle_webhook(_sub_updated("evt_early"), "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.TRIALING
        # ...but the later checkout projects LIVE state, so nothing from
        # the early event is actually lost.
        await service.handle_webhook(_checkout_completed(), "sig")
        sub = await repo.get(ALICE)
        assert sub.status is SubscriptionStatus.ACTIVE
        assert sub.plan is BillingPlan.MONTHLY
        assert sub.current_period_end == PERIOD_END


class TestProjectionUsesLiveState:
    async def test_stale_event_snapshot_is_ignored(self, service, repo, gateway):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(), "sig")
        # A stale event claims "canceled", but the live subscription is
        # active — refetch-and-project must trust the live state.
        gateway.subscriptions["sub_1"] = _live_state(status="active")
        await service.handle_webhook(
            _sub_updated("evt_stale", status="canceled"), "sig"
        )
        assert (await repo.get(ALICE)).status is SubscriptionStatus.ACTIVE

    async def test_live_cancellation_projects(self, service, repo, gateway):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(), "sig")
        gateway.subscriptions["sub_1"] = _live_state(status="canceled")
        await service.handle_webhook(
            _webhook(
                "evt_del",
                "customer.subscription.deleted",
                {"id": "sub_1", "customer": "cus_1"},
            ),
            "sig",
        )
        assert (await repo.get(ALICE)).status is SubscriptionStatus.CANCELED


class TestFailureDoesNotConsumeEvent:
    async def test_apply_failure_leaves_event_unrecorded_so_retry_works(
        self, service, repo, gateway
    ):
        await service.get_entitlements(ALICE)
        gateway.fail_next_get_subscription = True
        with pytest.raises(RuntimeError):
            await service.handle_webhook(_checkout_completed(), "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.TRIALING
        # Stripe retries the same event id; it must now apply.
        await service.handle_webhook(_checkout_completed(), "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.ACTIVE


class TestMalformedPayloads:
    @pytest.mark.parametrize(
        "data",
        [
            {"customer": "cus_1", "subscription": "sub_1"},  # no client_reference_id
            {"client_reference_id": ALICE, "subscription": "sub_1"},  # no customer
            {"client_reference_id": ALICE, "customer": "cus_1"},  # no subscription
            {"client_reference_id": None, "customer": "cus_1", "subscription": "s"},
        ],
    )
    async def test_bad_checkout_payload_raises_before_recording(
        self, service, repo, data
    ):
        await service.get_entitlements(ALICE)
        payload = _webhook("evt_bad", "checkout.session.completed", data)
        with pytest.raises(WebhookPayloadError):
            await service.handle_webhook(payload, "sig")
        # The event id must not be consumed: a corrected retry still applies.
        await service.handle_webhook(_checkout_completed("evt_bad"), "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.ACTIVE

    async def test_bad_subscription_payload_raises(self, service):
        payload = _webhook(
            "evt_bad2", "customer.subscription.updated", {"customer": "cus_1"}
        )
        with pytest.raises(WebhookPayloadError):
            await service.handle_webhook(payload, "sig")


class TestDuplicateDelivery:
    async def test_duplicate_produces_no_second_projection(self, service, gateway):
        await service.get_entitlements(ALICE)
        payload = _checkout_completed()
        await service.handle_webhook(payload, "sig")
        fetches_after_first = gateway.get_subscription_calls
        await service.handle_webhook(payload, "sig")
        assert gateway.get_subscription_calls == fetches_after_first


class TestDunningLadder:
    """Full payment-failure cascade, asserting the user-facing entitlement
    after every step — the sequence Stripe walks a failing card through."""

    async def test_active_to_past_due_to_canceled(self, service, repo, gateway):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(), "sig")
        assert (await service.get_entitlements(ALICE)).plan_status == "active"

        # First failed renewal: Stripe flips the subscription to past_due.
        # Access must be retained (Stripe is still retrying the card).
        gateway.subscriptions["sub_1"] = _live_state(status="past_due")
        await service.handle_webhook(_sub_updated("evt_dun_1"), "sig")
        ent = await service.get_entitlements(ALICE)
        assert ent.plan_status == "past_due"
        assert ent.read_only is False

        # Retries keep failing; another update arrives, still past_due.
        await service.handle_webhook(_sub_updated("evt_dun_2"), "sig")
        assert (await service.get_entitlements(ALICE)).plan_status == "past_due"

        # Stripe gives up: subscription deleted. By dunning exhaustion the
        # paid-through period is already behind us — a canceled sub with a
        # FUTURE period end would (correctly) retain paid-through access.
        gateway.subscriptions["sub_1"] = _live_state(
            status="canceled",
            current_period_end=datetime(2026, 7, 1, tzinfo=UTC),
        )
        await service.handle_webhook(
            _webhook(
                "evt_dun_3",
                "customer.subscription.deleted",
                {"id": "sub_1", "customer": "cus_1"},
            ),
            "sig",
        )
        ent = await service.get_entitlements(ALICE)
        assert ent.plan_status == "lapsed"
        assert ent.read_only is True

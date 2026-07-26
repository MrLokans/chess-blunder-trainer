import json
from datetime import UTC, datetime

import pytest

from blunder_tutor.auth import UserId
from blunder_tutor.billing.service import BillingService, NoStripeCustomerError
from blunder_tutor.billing.stripe_gateway import SubscriptionState
from blunder_tutor.billing.types import BillingPlan, SubscriptionStatus
from blunder_tutor.web.config import BillingConfig
from tests.billing.fakes import FakeStripeGateway

ALICE = UserId("a" * 32)
PERIOD_END = datetime.fromtimestamp(1790000000, tz=UTC)

CONFIG = BillingConfig(
    cloud_mode=True,
    stripe_secret_key="sk_test_x",
    stripe_webhook_secret="whsec_x",
    stripe_price_monthly="price_m",
    stripe_price_annual="price_a",
    public_base_url="https://cloud.example.com",
)


def _webhook(event_id: str, event_type: str, data: dict) -> bytes:
    return json.dumps(
        {"id": event_id, "type": event_type, "data": {"object": data}}
    ).encode()


def _checkout_completed(user_id: str) -> bytes:
    return _webhook(
        "evt_checkout",
        "checkout.session.completed",
        {"client_reference_id": user_id, "customer": "cus_1", "subscription": "sub_1"},
    )


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


class TestEntitlements:
    async def test_unknown_user_gets_trial_backfilled(self, service, repo):
        ent = await service.get_entitlements(ALICE)
        assert ent.plan_status == "trialing"
        assert (await repo.get(ALICE)).status is SubscriptionStatus.TRIALING

    async def test_cached_until_invalidated(self, service, repo):
        first = await service.get_entitlements(ALICE)
        await repo.apply_stripe_update(
            user_id=ALICE,
            customer_id="cus_1",
            subscription_id="sub_1",
            status=SubscriptionStatus.ACTIVE,
            plan=BillingPlan.MONTHLY,
            current_period_end=None,
        )
        assert (await service.get_entitlements(ALICE)).plan_status == first.plan_status
        service.invalidate(ALICE)
        assert (await service.get_entitlements(ALICE)).plan_status == "active"


class TestCheckout:
    async def test_returns_url_and_passes_price(self, service, gateway):
        url = await service.create_checkout(ALICE, BillingPlan.ANNUAL)
        assert url == "https://checkout.stripe.test/cs_1"
        call = gateway.checkout_calls[0]
        assert call["price_id"] == "price_a"
        assert call["user_id"] == ALICE
        assert call["success_url"].startswith("https://cloud.example.com")


class TestPortal:
    async def test_without_customer_raises(self, service):
        with pytest.raises(NoStripeCustomerError):
            await service.create_portal(ALICE)


class TestWebhooks:
    async def test_checkout_completed_activates(self, service, repo):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(ALICE), "sig")
        sub = await repo.get(ALICE)
        assert sub.status is SubscriptionStatus.ACTIVE
        assert sub.stripe_customer_id == "cus_1"

    async def test_subscription_updated_projects_live_plan_and_period(
        self, service, repo, gateway
    ):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(ALICE), "sig")
        gateway.subscriptions["sub_1"] = _live_state(status="past_due")
        payload = _webhook(
            "evt_2",
            "customer.subscription.updated",
            {"id": "sub_1", "customer": "cus_1"},
        )
        await service.handle_webhook(payload, "sig")
        sub = await repo.get(ALICE)
        assert sub.status is SubscriptionStatus.PAST_DUE
        assert sub.plan is BillingPlan.MONTHLY
        assert sub.current_period_end == PERIOD_END

    async def test_subscription_deleted_cancels(self, service, repo, gateway):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(ALICE), "sig")
        gateway.subscriptions["sub_1"] = _live_state(status="canceled")
        payload = _webhook(
            "evt_3",
            "customer.subscription.deleted",
            {"id": "sub_1", "customer": "cus_1"},
        )
        await service.handle_webhook(payload, "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.CANCELED

    async def test_duplicate_event_applied_once(self, service, repo):
        await service.get_entitlements(ALICE)
        payload = _checkout_completed(ALICE)
        await service.handle_webhook(payload, "sig")
        await service.handle_webhook(payload, "sig")
        assert (await repo.get(ALICE)).status is SubscriptionStatus.ACTIVE

    async def test_unknown_event_type_ignored(self, service):
        payload = _webhook("evt_x", "invoice.finalized", {"id": "in_1"})
        await service.handle_webhook(payload, "sig")

    async def test_unknown_customer_ignored(self, service):
        payload = _webhook(
            "evt_y",
            "customer.subscription.updated",
            {"id": "sub_9", "customer": "cus_unknown", "status": "active"},
        )
        await service.handle_webhook(payload, "sig")


class TestDeleteUser:
    async def test_cancels_stripe_and_removes_rows(self, service, repo, gateway):
        await service.get_entitlements(ALICE)
        await service.handle_webhook(_checkout_completed(ALICE), "sig")
        await service.delete_user(ALICE)
        assert gateway.canceled == ["sub_1"]
        assert await repo.get(ALICE) is None

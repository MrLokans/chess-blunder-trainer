"""Verified-fakes contract suite for the StripeGateway seam.

Every scenario runs against BOTH implementations:

- ``fake``: `FakeStripeGateway` — every CI run. This is what keeps the
  fake honest: any behavior asserted here is behavior the fake must
  share with reality.
- ``sandbox``: `HttpStripeGateway` against a real Stripe sandbox —
  marked ``integration`` (excluded from the default CI lane), executed
  by the scheduled `billing-contract` workflow and locally when
  ``STRIPE_TEST_SECRET_KEY`` is set. Skipped otherwise.

When these diverge, fix the FAKE (or the abstraction), never the test.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import stripe

from blunder_tutor.billing.stripe_gateway import (
    HttpStripeGateway,
    SubscriptionNotFoundError,
    SubscriptionState,
)
from tests.billing.fakes import FakeStripeGateway

SANDBOX_KEY_ENV = "STRIPE_TEST_SECRET_KEY"


class FakeHarness:
    def __init__(self) -> None:
        self.gateway = FakeStripeGateway()
        self.monthly_price_id = "price_contract_m"

    async def seed_subscription(self) -> tuple[str, str]:
        """Returns (subscription_id, expected_status)."""
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        self.gateway.subscriptions[sub_id] = SubscriptionState(
            subscription_id=sub_id,
            customer_id=f"cus_{uuid.uuid4().hex[:12]}",
            status="trialing",
            price_id=self.monthly_price_id,
            current_period_end=datetime.now(UTC) + timedelta(days=7),
        )
        return sub_id, "trialing"

    async def cleanup(self) -> None:
        return None


class SandboxHarness:
    """Drives a real Stripe sandbox. Creates a throwaway product/price/
    customer per run (tagged via metadata) and removes them on cleanup."""

    def __init__(self, secret_key: str) -> None:
        self.gateway = HttpStripeGateway(
            secret_key=secret_key, webhook_secret="whsec_contract_unused"
        )
        self._client = stripe.StripeClient(secret_key)
        self._run_tag = f"contract-{uuid.uuid4().hex[:8]}"
        price = self._client.v1.prices.create(
            params={
                "unit_amount": 700,
                "currency": "usd",
                "recurring": {"interval": "month"},
                "product_data": {"name": f"blunder-tutor {self._run_tag}"},
                "metadata": {"contract_run": self._run_tag},
            }
        )
        self.monthly_price_id = price.id
        self._customers: list[str] = []

    async def seed_subscription(self) -> tuple[str, str]:
        customer = self._client.v1.customers.create(
            params={"metadata": {"contract_run": self._run_tag}}
        )
        self._customers.append(customer.id)
        # A trial subscription needs no payment method and reaches a
        # stable status synchronously — the cheapest seedable state.
        sub = self._client.v1.subscriptions.create(
            params={
                "customer": customer.id,
                "items": [{"price": self.monthly_price_id}],
                "trial_period_days": 7,
            }
        )
        return sub.id, "trialing"

    async def cleanup(self) -> None:
        for customer_id in self._customers:
            self._client.v1.customers.delete(customer_id)


@pytest.fixture(
    params=[
        "fake",
        pytest.param("sandbox", marks=pytest.mark.integration),
    ]
)
async def harness(request):
    if request.param == "fake":
        yield FakeHarness()
        return
    secret_key = os.environ.get(SANDBOX_KEY_ENV, "")
    if not secret_key.startswith("sk_test_") and not secret_key.startswith("rk_test_"):
        pytest.skip(f"{SANDBOX_KEY_ENV} not set to a sandbox key")
    sandbox = SandboxHarness(secret_key)
    yield sandbox
    await sandbox.cleanup()


class TestGatewayContract:
    async def test_unknown_subscription_raises_not_found(self, harness):
        with pytest.raises(SubscriptionNotFoundError):
            await harness.gateway.get_subscription("sub_definitely_missing")

    async def test_seeded_subscription_roundtrip(self, harness):
        sub_id, expected_status = await harness.seed_subscription()
        state = await harness.gateway.get_subscription(sub_id)
        assert state.subscription_id == sub_id
        assert state.customer_id
        assert state.status == expected_status
        assert state.price_id == harness.monthly_price_id
        assert state.current_period_end is not None
        assert state.current_period_end.tzinfo is not None

    async def test_cancel_reflects_in_subsequent_get(self, harness):
        sub_id, _ = await harness.seed_subscription()
        await harness.gateway.cancel_subscription(sub_id)
        state = await harness.gateway.get_subscription(sub_id)
        assert state.status == "canceled"

    async def test_checkout_session_returns_https_url(self, harness):
        session = await harness.gateway.create_checkout_session(
            user_id="a" * 32,
            customer_id=None,
            price_id=harness.monthly_price_id,
            success_url="https://cloud.example.com/settings?billing=success",
            cancel_url="https://cloud.example.com/settings?billing=canceled",
        )
        assert session.url.startswith("https://")

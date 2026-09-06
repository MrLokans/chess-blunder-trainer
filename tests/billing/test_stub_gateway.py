import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from blunder_tutor.billing.gateway_factory import create_gateway
from blunder_tutor.billing.stripe_gateway import (
    HttpStripeGateway,
    SubscriptionNotFoundError,
    WebhookVerificationError,
)
from blunder_tutor.billing.stub_gateway import (
    StubStripeGateway,
    parse_stub_subscription_id,
)
from blunder_tutor.billing.types import BillingPlan
from blunder_tutor.web.config import BillingConfig

STUB_SECRET = "whsec_e2e_stub_secret"

CONFIG = BillingConfig(
    cloud_mode=True,
    stripe_secret_key="sk_test_stub",
    stripe_webhook_secret=STUB_SECRET,
    stripe_price_monthly="price_m",
    stripe_price_annual="price_a",
    public_base_url="http://localhost:8002",
    stripe_stub=True,
)


class TestParseStubSubscriptionId:
    @pytest.mark.parametrize(
        ("sub_id", "expected"),
        [
            ("sub_stub_active_monthly", ("active", BillingPlan.MONTHLY)),
            ("sub_stub_past_due", ("past_due", None)),
            ("sub_stub_canceled_annual", ("canceled", BillingPlan.ANNUAL)),
            ("sub_stub_trialing", ("trialing", None)),
        ],
    )
    def test_valid_ids(self, sub_id, expected):
        assert parse_stub_subscription_id(sub_id) == expected

    @pytest.mark.parametrize("sub_id", ["sub_real_123", "sub_stub_bogus", ""])
    def test_invalid_ids_raise(self, sub_id):
        with pytest.raises(SubscriptionNotFoundError):
            parse_stub_subscription_id(sub_id)


class TestStubGateway:
    async def test_active_monthly_state(self):
        gateway = StubStripeGateway(CONFIG)
        state = await gateway.get_subscription("sub_stub_active_monthly")
        assert state.status == "active"
        assert state.price_id == "price_m"
        assert state.current_period_end > datetime.now(UTC)

    async def test_canceled_period_is_past(self):
        gateway = StubStripeGateway(CONFIG)
        state = await gateway.get_subscription("sub_stub_canceled")
        assert state.status == "canceled"
        assert state.current_period_end < datetime.now(UTC)

    async def test_checkout_url_is_local(self):
        gateway = StubStripeGateway(CONFIG)
        session = await gateway.create_checkout_session(
            user_id="u",
            customer_id=None,
            price_id="price_m",
            success_url="x",
            cancel_url="y",
        )
        assert session.url.startswith("http://localhost:8002/settings")

    def test_signature_verification_stays_real(self):
        gateway = StubStripeGateway(CONFIG)
        payload = json.dumps(
            {"id": "evt_1", "object": "event", "type": "x", "data": {"object": {}}}
        ).encode()
        ts = int(time.time())
        good = hmac.new(
            STUB_SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256
        ).hexdigest()
        event = gateway.verify_webhook(payload, f"t={ts},v1={good}")
        assert event.event_id == "evt_1"
        with pytest.raises(WebhookVerificationError):
            gateway.verify_webhook(payload, f"t={ts},v1={'0' * 64}")


class TestCreateGateway:
    def test_stub_flag_selects_stub(self):
        assert isinstance(create_gateway(CONFIG), StubStripeGateway)

    def test_default_selects_http(self):
        real = CONFIG.model_copy(update={"stripe_stub": False})
        gateway = create_gateway(real)
        assert isinstance(gateway, HttpStripeGateway)
        assert not isinstance(gateway, StubStripeGateway)


class TestStubConfigGuard:
    def test_live_key_with_stub_rejected(self):
        with pytest.raises(ValidationError, match="live Stripe key"):
            BillingConfig(
                cloud_mode=True,
                stripe_secret_key="sk_live_oops",
                stripe_webhook_secret="whsec_x",
                stripe_price_monthly="m",
                stripe_price_annual="a",
                public_base_url="https://x",
                stripe_stub=True,
            )

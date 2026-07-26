import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

import pytest

from blunder_tutor.billing.stripe_gateway import (
    HttpStripeGateway,
    WebhookVerificationError,
    subscription_state_from_api,
)

SECRET = "whsec_test_secret"

# Real Stripe payloads always carry a top-level `"object": "event"`;
# construct_event dispatches on it in stripe>=15.
EVENT = {
    "id": "evt_1",
    "object": "event",
    "type": "customer.subscription.updated",
    "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "active"}},
}


def _sign(payload: bytes, secret: str, timestamp: int) -> str:
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.fixture
def gateway() -> HttpStripeGateway:
    return HttpStripeGateway(secret_key="sk_test_x", webhook_secret=SECRET)


class TestVerifyWebhook:
    def test_valid_signature_parses_event(self, gateway):
        payload = json.dumps(EVENT).encode()
        sig = _sign(payload, SECRET, int(time.time()))
        event = gateway.verify_webhook(payload, sig)
        assert event.event_id == "evt_1"
        assert event.event_type == "customer.subscription.updated"
        assert event.data["customer"] == "cus_1"

    def test_wrong_secret_raises(self, gateway):
        payload = json.dumps(EVENT).encode()
        sig = _sign(payload, "whsec_wrong", int(time.time()))
        with pytest.raises(WebhookVerificationError):
            gateway.verify_webhook(payload, sig)

    def test_stale_timestamp_raises(self, gateway):
        payload = json.dumps(EVENT).encode()
        sig = _sign(payload, SECRET, int(time.time()) - 3600)
        with pytest.raises(WebhookVerificationError):
            gateway.verify_webhook(payload, sig)

    def test_garbage_payload_raises(self, gateway):
        with pytest.raises(WebhookVerificationError):
            gateway.verify_webhook(b"not json", "t=1,v1=abc")


PERIOD_END_TS = 1790000000

# Shape used by API versions before 2025-03-31 "basil":
# current_period_end lives on the subscription top level.
PRE_BASIL_SUBSCRIPTION = {
    "id": "sub_1",
    "customer": "cus_1",
    "status": "active",
    "current_period_end": PERIOD_END_TS,
    "items": {"data": [{"price": {"id": "price_m"}}]},
}

# Shape from "basil" onward: current_period_end moved onto each
# subscription item; the top-level field is gone.
BASIL_SUBSCRIPTION = {
    "id": "sub_1",
    "customer": "cus_1",
    "status": "active",
    "items": {
        "data": [{"price": {"id": "price_m"}, "current_period_end": PERIOD_END_TS}]
    },
}


class TestSubscriptionStateFromApi:
    @pytest.mark.parametrize("payload", [PRE_BASIL_SUBSCRIPTION, BASIL_SUBSCRIPTION])
    def test_both_api_shapes_yield_same_state(self, payload):
        state = subscription_state_from_api(payload)
        assert state.subscription_id == "sub_1"
        assert state.customer_id == "cus_1"
        assert state.status == "active"
        assert state.price_id == "price_m"
        assert state.current_period_end == datetime.fromtimestamp(PERIOD_END_TS, tz=UTC)

    def test_expanded_customer_object(self):
        payload = {**PRE_BASIL_SUBSCRIPTION, "customer": {"id": "cus_1"}}
        assert subscription_state_from_api(payload).customer_id == "cus_1"

    def test_missing_optionals_survive(self):
        state = subscription_state_from_api(
            {"id": "sub_1", "customer": "cus_1", "status": "canceled"}
        )
        assert state.price_id is None
        assert state.current_period_end is None

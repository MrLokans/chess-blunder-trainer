import hashlib
import hmac
import json
import time

import pytest

from blunder_tutor.billing.stripe_gateway import (
    HttpStripeGateway,
    WebhookVerificationError,
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

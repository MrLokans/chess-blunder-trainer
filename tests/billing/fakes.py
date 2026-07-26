import json

from blunder_tutor.billing.stripe_gateway import (
    CheckoutSession,
    SubscriptionState,
    WebhookEvent,
    WebhookVerificationError,
)


class FakeStripeGateway:
    def __init__(self) -> None:
        self.checkout_calls: list[dict] = []
        self.portal_calls: list[dict] = []
        self.canceled: list[str] = []
        self.reject_webhooks = False
        self.subscriptions: dict[str, SubscriptionState] = {}
        self.get_subscription_calls = 0
        self.fail_next_get_subscription = False

    async def create_checkout_session(self, **kwargs) -> CheckoutSession:
        self.checkout_calls.append(kwargs)
        return CheckoutSession(url="https://checkout.stripe.test/cs_1")

    async def create_portal_session(self, **kwargs) -> str:
        self.portal_calls.append(kwargs)
        return "https://portal.stripe.test/ps_1"

    async def cancel_subscription(self, subscription_id: str) -> None:
        self.canceled.append(subscription_id)

    async def get_subscription(self, subscription_id: str) -> SubscriptionState:
        if self.fail_next_get_subscription:
            self.fail_next_get_subscription = False
            raise RuntimeError("simulated stripe outage")
        self.get_subscription_calls += 1
        return self.subscriptions[subscription_id]

    def verify_webhook(self, payload: bytes, sig_header: str) -> WebhookEvent:
        if self.reject_webhooks:
            raise WebhookVerificationError("bad signature")
        parsed = json.loads(payload)
        return WebhookEvent(
            event_id=parsed["id"],
            event_type=parsed["type"],
            data=parsed["data"]["object"],
        )

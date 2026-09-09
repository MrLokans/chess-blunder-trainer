import json
from datetime import datetime, timedelta

from blunder_tutor.billing.stripe_gateway import (
    CheckoutSession,
    SubscriptionNotFoundError,
    SubscriptionState,
    WebhookEvent,
    WebhookVerificationError,
)


class ControlledClock:
    """Injectable clock for driving trial/period boundaries through the
    domain instead of mutating DB rows."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


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
        stored = self.subscriptions.get(subscription_id)
        if stored is not None:
            self.subscriptions[subscription_id] = SubscriptionState(
                subscription_id=stored.subscription_id,
                customer_id=stored.customer_id,
                status="canceled",
                price_id=stored.price_id,
                current_period_end=stored.current_period_end,
            )

    async def get_subscription(self, subscription_id: str) -> SubscriptionState:
        if self.fail_next_get_subscription:
            self.fail_next_get_subscription = False
            raise RuntimeError("simulated stripe outage")
        self.get_subscription_calls += 1
        try:
            return self.subscriptions[subscription_id]
        except KeyError as exc:
            raise SubscriptionNotFoundError(subscription_id) from exc

    def verify_webhook(self, payload: bytes, sig_header: str) -> WebhookEvent:
        if self.reject_webhooks:
            raise WebhookVerificationError("bad signature")
        parsed = json.loads(payload)
        return WebhookEvent(
            event_id=parsed["id"],
            event_type=parsed["type"],
            data=parsed["data"]["object"],
        )

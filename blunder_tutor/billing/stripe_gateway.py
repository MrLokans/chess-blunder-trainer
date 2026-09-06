from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import stripe

from blunder_tutor.web.config import BillingConfig


class WebhookVerificationError(Exception):
    """Signature or payload rejected — respond 400, never process."""


class SubscriptionNotFoundError(Exception):
    """No subscription with that id — normalized across implementations
    so callers and the contract suite never depend on SDK error types."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckoutSession:
    url: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WebhookEvent:
    event_id: str
    event_type: str
    data: dict


@dataclass(frozen=True, slots=True, kw_only=True)
class SubscriptionState:
    """Live subscription state retrieved from Stripe.

    Webhook payload shapes follow the endpoint's pinned API version and
    have moved fields across major releases (`current_period_end` left
    the subscription top level in 2025's "basil"). Retrieved objects
    follow the SDK's own pinned version instead, so projecting from a
    retrieve keeps the parser stable regardless of webhook endpoint
    configuration.
    """

    subscription_id: str
    customer_id: str
    status: str
    price_id: str | None
    current_period_end: datetime | None


def _field(source: Any, key: str, default: Any = None) -> Any:
    """Read a key from a dict OR a StripeObject (both support [] with
    KeyError on miss; StripeObject is not a dict subclass in stripe>=15)."""
    try:
        return source[key]
    except (KeyError, TypeError):
        return default


_ID_KEY = "id"


def subscription_state_from_api(sub: Any) -> SubscriptionState:
    items = _field(_field(sub, "items") or {}, "data") or []
    first_item = items[0] if items else None
    period_end_ts = _field(sub, "current_period_end")
    if period_end_ts is None and first_item is not None:
        period_end_ts = _field(first_item, "current_period_end")
    price_id = None
    if first_item is not None:
        price_id = _field(_field(first_item, "price") or {}, _ID_KEY)
    customer = _field(sub, "customer")
    if not isinstance(customer, str):
        customer = _field(customer or {}, _ID_KEY)
    return SubscriptionState(
        subscription_id=_field(sub, _ID_KEY),
        customer_id=customer,
        status=_field(sub, "status") or "",
        price_id=price_id,
        current_period_end=(
            datetime.fromtimestamp(period_end_ts, tz=UTC) if period_end_ts else None
        ),
    )


class StripeGateway(Protocol):
    async def create_checkout_session(
        self,
        *,
        user_id: str,
        customer_id: str | None,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession: ...

    async def create_portal_session(
        self, *, customer_id: str, return_url: str
    ) -> str: ...

    async def cancel_subscription(self, subscription_id: str) -> None: ...

    async def get_subscription(self, subscription_id: str) -> SubscriptionState: ...

    def verify_webhook(self, payload: bytes, sig_header: str) -> WebhookEvent: ...


class HttpStripeGateway:
    def __init__(self, *, secret_key: str, webhook_secret: str) -> None:
        client = stripe.StripeClient(secret_key)
        self._checkout_sessions = client.v1.checkout.sessions
        self._portal_sessions = client.v1.billing_portal.sessions
        self._subscriptions = client.v1.subscriptions
        self._webhook_secret = webhook_secret

    async def create_checkout_session(
        self,
        *,
        user_id: str,
        customer_id: str | None,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        params: dict = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "client_reference_id": user_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if customer_id:
            params["customer"] = customer_id
        session = await asyncio.to_thread(self._checkout_sessions.create, params=params)
        return CheckoutSession(url=session.url)

    async def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        session = await asyncio.to_thread(
            self._portal_sessions.create,
            params={"customer": customer_id, "return_url": return_url},
        )
        return session.url

    async def cancel_subscription(self, subscription_id: str) -> None:
        await asyncio.to_thread(self._subscriptions.cancel, subscription_id)

    async def get_subscription(self, subscription_id: str) -> SubscriptionState:
        try:
            sub = await asyncio.to_thread(self._subscriptions.retrieve, subscription_id)
        except stripe.InvalidRequestError as exc:
            raise SubscriptionNotFoundError(subscription_id) from exc
        return subscription_state_from_api(sub)

    def verify_webhook(self, payload: bytes, sig_header: str) -> WebhookEvent:
        try:
            stripe.Webhook.construct_event(payload, sig_header, self._webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise WebhookVerificationError(str(exc)) from exc
        # Signature is verified above; re-parse the raw payload so the
        # returned data is a plain dict independent of SDK object quirks.
        parsed = json.loads(payload)
        return WebhookEvent(
            event_id=parsed["id"],
            event_type=parsed["type"],
            data=parsed["data"]["object"],
        )


def build_stripe_gateway(config: BillingConfig) -> StripeGateway:
    assert config.stripe_secret_key is not None  # validated by BillingConfig
    assert config.stripe_webhook_secret is not None
    return HttpStripeGateway(
        secret_key=config.stripe_secret_key,
        webhook_secret=config.stripe_webhook_secret,
    )

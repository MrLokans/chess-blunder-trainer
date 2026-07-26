from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Protocol

import stripe

from blunder_tutor.web.config import BillingConfig


class WebhookVerificationError(Exception):
    """Signature or payload rejected — respond 400, never process."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckoutSession:
    url: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WebhookEvent:
    event_id: str
    event_type: str
    data: dict


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

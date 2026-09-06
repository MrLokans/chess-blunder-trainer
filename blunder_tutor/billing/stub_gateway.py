from __future__ import annotations

import logging
from datetime import timedelta

from blunder_tutor.billing.stripe_gateway import (
    CheckoutSession,
    HttpStripeGateway,
    SubscriptionNotFoundError,
    SubscriptionState,
)
from blunder_tutor.billing.types import BillingPlan
from blunder_tutor.utils.time import utcnow
from blunder_tutor.web.config import BillingConfig

log = logging.getLogger(__name__)

_STUB_PREFIX = "sub_stub_"
_STUB_STATUSES = frozenset(("trialing", "active", "past_due", "canceled"))
_STUB_PERIOD_DAYS = 30


def parse_stub_subscription_id(
    subscription_id: str,
) -> tuple[str, BillingPlan | None]:
    """Decode `sub_stub_<status>[_<plan>]` into (status, plan).

    The stub is stateless; E2E tests choose the projected outcome by
    encoding it in the subscription id they put on the webhook event
    (e.g. `sub_stub_active_monthly`, `sub_stub_past_due`,
    `sub_stub_canceled`).
    """
    if not subscription_id.startswith(_STUB_PREFIX):
        raise SubscriptionNotFoundError(subscription_id)
    remainder = subscription_id.removeprefix(_STUB_PREFIX)
    plan: BillingPlan | None = None
    for candidate in BillingPlan:
        suffix = f"_{candidate.value}"
        if remainder.endswith(suffix):
            plan = candidate
            remainder = remainder.removesuffix(suffix)
            break
    if remainder not in _STUB_STATUSES:
        raise SubscriptionNotFoundError(subscription_id)
    return remainder, plan


class StubStripeGateway(HttpStripeGateway):
    """Network-free gateway for E2E and demo deployments.

    Inherits the REAL webhook signature verification from
    :class:`HttpStripeGateway` (tests sign payloads with the configured
    secret) and replaces every network call with deterministic local
    behavior. Never enable outside test/demo environments.
    """

    def __init__(self, config: BillingConfig) -> None:
        super().__init__(
            secret_key=config.stripe_secret_key or "sk_test_stub",
            webhook_secret=config.stripe_webhook_secret or "whsec_stub",
        )
        self._stub_config = config

    async def create_checkout_session(self, **_kwargs) -> CheckoutSession:
        base = self._stub_config.public_base_url
        return CheckoutSession(url=f"{base}/settings?billing=stub-checkout")

    async def create_portal_session(self, **_kwargs) -> str:
        return f"{self._stub_config.public_base_url}/settings?billing=stub-portal"

    async def cancel_subscription(self, subscription_id: str) -> None:
        log.info("billing.stub.cancel subscription=%s", subscription_id)

    async def get_subscription(self, subscription_id: str) -> SubscriptionState:
        status, plan = parse_stub_subscription_id(subscription_id)
        if status == "canceled":
            period_end = utcnow() - timedelta(days=1)
        else:
            period_end = utcnow() + timedelta(days=_STUB_PERIOD_DAYS)
        price_id = None
        if plan is BillingPlan.MONTHLY:
            price_id = self._stub_config.stripe_price_monthly
        elif plan is BillingPlan.ANNUAL:
            price_id = self._stub_config.stripe_price_annual
        return SubscriptionState(
            subscription_id=subscription_id,
            customer_id="cus_stub",
            status=status,
            price_id=price_id,
            current_period_end=period_end,
        )

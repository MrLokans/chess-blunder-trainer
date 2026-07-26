from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

from blunder_tutor.auth import UserId
from blunder_tutor.billing.entitlements import Entitlements, resolve_entitlements
from blunder_tutor.billing.repository import SubscriptionRepository
from blunder_tutor.billing.stripe_gateway import StripeGateway
from blunder_tutor.billing.types import BillingPlan, Subscription, SubscriptionStatus
from blunder_tutor.web.config import BillingConfig

log = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60.0

_STRIPE_STATUS_MAP = MappingProxyType(
    {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "incomplete": SubscriptionStatus.PAST_DUE,
        "unpaid": SubscriptionStatus.CANCELED,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete_expired": SubscriptionStatus.CANCELED,
    }
)

_CUSTOMER_KEY = "customer"

_SUBSCRIPTION_EVENT_TYPES = frozenset(
    ("customer.subscription.updated", "customer.subscription.deleted")
)


class NoStripeCustomerError(Exception):
    """Portal requested before the user ever completed a checkout."""


class WebhookPayloadError(Exception):
    """Required field missing/invalid — respond 400 before recording the
    event, so a corrected redelivery is not swallowed by dedup."""


def _require(data: dict, key: str) -> str:
    field_value = data.get(key)
    if not isinstance(field_value, str) or not field_value:
        raise WebhookPayloadError(f"missing or invalid field: {key}")
    return field_value


def _plan_from_price(price_id: str | None, config: BillingConfig) -> BillingPlan | None:
    if price_id == config.stripe_price_monthly:
        return BillingPlan.MONTHLY
    if price_id == config.stripe_price_annual:
        return BillingPlan.ANNUAL
    return None


class BillingService:
    def __init__(
        self,
        *,
        repo: SubscriptionRepository,
        gateway: StripeGateway,
        config: BillingConfig,
    ) -> None:
        self._repo = repo
        self._gateway = gateway
        self._config = config
        self._cache: dict[str, tuple[Entitlements, float]] = {}

    async def start_trial(self, user_id: UserId) -> None:
        trial_ends = datetime.now(UTC) + timedelta(days=self._config.trial_days)
        await self._repo.start_trial(
            user_id=user_id,
            trial_ends_at=trial_ends,
            node_id=self._config.node_id,
        )

    async def get_entitlements(self, user_id: UserId) -> Entitlements:
        cached = self._cache.get(user_id)
        if cached is not None and time.monotonic() - cached[1] < _CACHE_TTL_SECONDS:
            return cached[0]
        sub = await self._repo.get(user_id)
        if sub is None:
            # Users created before cloud mode was enabled have no row yet.
            await self.start_trial(user_id)
            sub = await self._repo.get(user_id)
        entitlements = resolve_entitlements(sub, datetime.now(UTC))
        self._cache[user_id] = (entitlements, time.monotonic())
        return entitlements

    def invalidate(self, user_id: str) -> None:
        self._cache.pop(user_id, None)

    async def get_subscription(self, user_id: UserId) -> Subscription | None:
        return await self._repo.get(user_id)

    async def create_checkout(self, user_id: UserId, plan: BillingPlan) -> str:
        price = (
            self._config.stripe_price_monthly
            if plan is BillingPlan.MONTHLY
            else self._config.stripe_price_annual
        )
        sub = await self._repo.get(user_id)
        base = self._config.public_base_url
        session = await self._gateway.create_checkout_session(
            user_id=user_id,
            customer_id=sub.stripe_customer_id if sub else None,
            price_id=price,
            success_url=f"{base}/settings?billing=success",
            cancel_url=f"{base}/settings?billing=canceled",
        )
        return session.url

    async def create_portal(self, user_id: UserId) -> str:
        sub = await self._repo.get(user_id)
        if sub is None or sub.stripe_customer_id is None:
            raise NoStripeCustomerError()
        return await self._gateway.create_portal_session(
            customer_id=sub.stripe_customer_id,
            return_url=f"{self._config.public_base_url}/settings",
        )

    async def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        """Verify, dedup, apply, THEN record.

        Recording only after a successful apply means any failure
        (Stripe outage during refetch, DB error) leaves the event
        unconsumed, so Stripe's redelivery of the same event id still
        applies — the inverse order permanently loses events. Handlers
        are idempotent projections of live state, so the benign race of
        two concurrent deliveries both passing the dedup check is safe.
        """
        event = self._gateway.verify_webhook(payload, sig_header)
        if await self._repo.event_processed(event.event_id):
            return
        if event.event_type == "checkout.session.completed":
            await self._on_checkout_completed(event.data)
        elif event.event_type in _SUBSCRIPTION_EVENT_TYPES:
            await self._on_subscription_event(event.data)
        else:
            log.debug("billing.webhook.ignored type=%s", event.event_type)
        await self._repo.record_event(event.event_id)

    async def delete_user(self, user_id: UserId) -> None:
        sub = await self._repo.get(user_id)
        if sub is not None and sub.stripe_subscription_id is not None:
            try:
                await self._gateway.cancel_subscription(sub.stripe_subscription_id)
            except Exception:
                log.exception("billing.delete.stripe_cancel_failed user=%s", user_id)
        await self._repo.delete_user(user_id)
        self.invalidate(user_id)

    async def _on_checkout_completed(self, data: dict) -> None:
        user_id = UserId(_require(data, "client_reference_id"))
        customer_id = _require(data, _CUSTOMER_KEY)
        subscription_id = _require(data, "subscription")
        row = await self._repo.get(user_id)
        if row is None:
            log.warning("billing.webhook.unknown_user user=%s", user_id)
            return
        await self._project_subscription(customer_id, subscription_id, row)

    async def _on_subscription_event(self, data: dict) -> None:
        customer_id = _require(data, _CUSTOMER_KEY)
        subscription_id = _require(data, "id")
        row = await self._repo.find_by_customer(customer_id)
        if row is None:
            # Likely out-of-order arrival before checkout.session.completed.
            # Safe to absorb: the checkout handler projects live state, so
            # nothing carried by this event is actually lost.
            log.warning("billing.webhook.unknown_customer customer=%s", customer_id)
            return
        await self._project_subscription(customer_id, subscription_id, row)

    async def _project_subscription(
        self, customer_id: str, subscription_id: str, row: Subscription
    ) -> None:
        """Refetch-and-project: webhook events are treated as nudges and
        the live subscription is the source of truth. Delivery order and
        stale embedded snapshots then stop mattering, and the parser only
        has to understand the SDK-pinned retrieve shape — not whatever
        API version the webhook endpoint is pinned to."""
        live = await self._gateway.get_subscription(subscription_id)
        await self._repo.apply_stripe_update(
            user_id=row.user_id,
            customer_id=customer_id,
            subscription_id=subscription_id,
            status=_STRIPE_STATUS_MAP.get(live.status, row.status),
            plan=_plan_from_price(live.price_id, self._config) or row.plan,
            current_period_end=live.current_period_end or row.current_period_end,
        )
        self.invalidate(row.user_id)

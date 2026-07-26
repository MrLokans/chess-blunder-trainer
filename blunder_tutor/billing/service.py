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


def _plan_from_items(data: dict, config: BillingConfig) -> BillingPlan | None:
    items = data.get("items", {}).get("data", [])
    if not items:
        return None
    price_id = items[0].get("price", {}).get("id")
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

    @property
    def gateway(self) -> StripeGateway:
        return self._gateway

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
        event = self._gateway.verify_webhook(payload, sig_header)
        if not await self._repo.record_event(event.event_id):
            return
        if event.event_type == "checkout.session.completed":
            await self._on_checkout_completed(event.data)
        elif event.event_type in _SUBSCRIPTION_EVENT_TYPES:
            await self._on_subscription_event(event.data)
        else:
            log.debug("billing.webhook.ignored type=%s", event.event_type)

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
        user_id = UserId(data["client_reference_id"])
        existing = await self._repo.get(user_id)
        if existing is None:
            log.warning("billing.webhook.unknown_user user=%s", user_id)
            return
        await self._repo.apply_stripe_update(
            user_id=user_id,
            customer_id=data[_CUSTOMER_KEY],
            subscription_id=data["subscription"],
            status=SubscriptionStatus.ACTIVE,
            plan=existing.plan,
            current_period_end=existing.current_period_end,
        )
        self.invalidate(user_id)

    async def _on_subscription_event(self, data: dict) -> None:
        sub = await self._repo.find_by_customer(data[_CUSTOMER_KEY])
        if sub is None:
            log.warning(
                "billing.webhook.unknown_customer customer=%s", data[_CUSTOMER_KEY]
            )
            return
        status = _STRIPE_STATUS_MAP.get(data.get("status", ""), sub.status)
        period_end_ts = data.get("current_period_end")
        period_end = (
            datetime.fromtimestamp(period_end_ts, tz=UTC) if period_end_ts else None
        )
        await self._repo.apply_stripe_update(
            user_id=sub.user_id,
            customer_id=data[_CUSTOMER_KEY],
            subscription_id=data["id"],
            status=status,
            plan=_plan_from_items(data, self._config) or sub.plan,
            current_period_end=period_end or sub.current_period_end,
        )
        self.invalidate(sub.user_id)

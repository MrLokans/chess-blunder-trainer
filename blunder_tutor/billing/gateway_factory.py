from __future__ import annotations

import logging

from blunder_tutor.billing.stripe_gateway import StripeGateway, build_stripe_gateway
from blunder_tutor.billing.stub_gateway import StubStripeGateway
from blunder_tutor.web.config import BillingConfig

log = logging.getLogger(__name__)


def create_gateway(config: BillingConfig) -> StripeGateway:
    if config.stripe_stub:
        log.warning(
            "BILLING STRIPE STUB ACTIVE — no real Stripe calls will be made. "
            "This mode is for E2E tests and demo deployments only."
        )
        return StubStripeGateway(config)
    return build_stripe_gateway(config)

from __future__ import annotations

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from blunder_tutor.billing.entitlements import CLOUD_GRANTS
from blunder_tutor.web.middleware import MUTATION_METHODS
from blunder_tutor.web.paths import AUTH_API_PREFIX, BILLING_API_PREFIX

# Lapsed users must always be able to authenticate, pay, and leave.
LAPSED_ALLOWED_PREFIXES: tuple[str, ...] = (
    AUTH_API_PREFIX,
    BILLING_API_PREFIX,
    "/logout",
    "/api/settings/locale",
)


class BillingGateMiddleware(BaseHTTPMiddleware):
    """Resolve entitlements per request and enforce read-only on lapse.

    Always registered, but bails immediately when ``app.state.billing``
    is ``None`` (cloud mode off), keeping self-host behavior untouched.
    """

    async def dispatch(self, request: Request, call_next):
        billing = getattr(request.app.state, "billing", None)
        if billing is None:
            return await call_next(request)
        ctx = getattr(request.state, "user_ctx", None)
        if ctx is None or not ctx.is_authenticated:
            return await call_next(request)

        entitlements = await billing.service.get_entitlements(ctx.user_id)
        request.state.entitlements = entitlements
        request.state.entitlement_grants = {
            grant: grant in entitlements.grants for grant in CLOUD_GRANTS
        }

        blocked = (
            entitlements.read_only
            and request.method in MUTATION_METHODS
            and not request.url.path.startswith(LAPSED_ALLOWED_PREFIXES)
        )
        if blocked:
            return JSONResponse(
                {
                    "error": "subscription_required",
                    "message": "Subscription required to make changes",
                },
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
            )
        return await call_next(request)

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from blunder_tutor.auth.fastapi.dependencies import UserContextDep
from blunder_tutor.billing.service import (
    BillingService,
    NoStripeCustomerError,
    WebhookPayloadError,
)
from blunder_tutor.billing.stripe_gateway import WebhookVerificationError
from blunder_tutor.billing.types import BillingPlan

router = APIRouter(prefix="/api/billing")


def get_billing_service(request: Request) -> BillingService:
    billing = request.app.state.billing
    if billing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="cloud_mode_disabled"
        )
    return billing.service


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]


class CheckoutRequest(BaseModel):
    plan: Literal["monthly", "annual"]


class UrlResponse(BaseModel):
    url: str


class StatusResponse(BaseModel):
    status: str
    plan: str | None
    trial_ends_at: str | None
    current_period_end: str | None
    read_only: bool
    grants: list[str]


class WebhookAck(BaseModel):
    received: bool


@router.get("/status")
async def billing_status(
    ctx: UserContextDep, service: BillingServiceDep
) -> StatusResponse:
    entitlements = await service.get_entitlements(ctx.user_id)
    sub = await service.get_subscription(ctx.user_id)
    return StatusResponse(
        status=entitlements.plan_status,
        plan=sub.plan.value if sub and sub.plan else None,
        trial_ends_at=(
            entitlements.trial_ends_at.isoformat()
            if entitlements.trial_ends_at
            else None
        ),
        current_period_end=(
            sub.current_period_end.isoformat()
            if sub and sub.current_period_end
            else None
        ),
        read_only=entitlements.read_only,
        grants=sorted(entitlements.grants),
    )


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest, ctx: UserContextDep, service: BillingServiceDep
) -> UrlResponse:
    url = await service.create_checkout(ctx.user_id, BillingPlan(body.plan))
    return UrlResponse(url=url)


@router.post("/portal")
async def create_portal(ctx: UserContextDep, service: BillingServiceDep) -> UrlResponse:
    try:
        url = await service.create_portal(ctx.user_id)
    except NoStripeCustomerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="no_customer"
        ) from exc
    return UrlResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request, service: BillingServiceDep) -> WebhookAck:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        await service.handle_webhook(payload, signature)
    except WebhookVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_signature"
        ) from exc
    except WebhookPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_payload"
        ) from exc
    return WebhookAck(received=True)

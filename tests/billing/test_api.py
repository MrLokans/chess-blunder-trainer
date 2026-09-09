import json

from blunder_tutor.billing.stripe_gateway import SubscriptionState
from tests.billing.conftest import signup_first_user


def _webhook(event_id: str, event_type: str, data: dict) -> bytes:
    return json.dumps(
        {"id": event_id, "type": event_type, "data": {"object": data}}
    ).encode()


class TestStatus:
    async def test_after_signup_shows_trialing(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.get("/api/billing/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "trialing"
        assert body["read_only"] is False
        assert "cloud.autosync" in body["grants"]

    async def test_404_when_cloud_off(self, client_credentials_mode, invite_code):
        signup = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert signup.status_code == 200
        resp = await client_credentials_mode.get("/api/billing/status")
        assert resp.status_code == 404

    async def test_requires_auth(self, cloud_client):
        resp = await cloud_client.get("/api/billing/status")
        assert resp.status_code == 401


class TestCheckout:
    async def test_returns_stripe_url(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.post(
            "/api/billing/checkout", json={"plan": "monthly"}
        )
        assert resp.status_code == 200
        assert resp.json()["url"].startswith("https://checkout.stripe.test/")

    async def test_rejects_unknown_plan(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.post(
            "/api/billing/checkout", json={"plan": "lifetime"}
        )
        assert resp.status_code == 422


class TestPortal:
    async def test_before_checkout_409(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.post("/api/billing/portal", json={})
        assert resp.status_code == 409


class TestWebhook:
    async def test_unauthenticated_post_accepted(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        cloud_app.state.fake_stripe.subscriptions["sub_1"] = SubscriptionState(
            subscription_id="sub_1",
            customer_id="cus_1",
            status="active",
            price_id="price_m",
            current_period_end=None,
        )
        payload = _webhook(
            "evt_1",
            "checkout.session.completed",
            {
                "client_reference_id": user_id,
                "customer": "cus_1",
                "subscription": "sub_1",
            },
        )
        resp = await cloud_client.post(
            "/api/billing/webhook",
            content=payload,
            headers={"stripe-signature": "sig", "origin": "https://evil.example"},
        )
        assert resp.status_code == 200
        status = await cloud_client.get("/api/billing/status")
        assert status.json()["status"] == "active"

    async def test_bad_signature_400(self, cloud_app, cloud_client):
        cloud_app.state.fake_stripe.reject_webhooks = True
        resp = await cloud_client.post(
            "/api/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "bad"},
        )
        assert resp.status_code == 400

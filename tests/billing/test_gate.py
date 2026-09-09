from datetime import UTC, datetime, timedelta

from tests.billing.conftest import signup_first_user


async def _force_lapse(cloud_app, user_id: str) -> None:
    db = cloud_app.state.billing.db
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    async with db.write() as conn:
        await conn.execute(
            "UPDATE subscriptions SET trial_ends_at = ? WHERE user_id = ?",
            (past, user_id),
        )
    cloud_app.state.billing.service.invalidate(user_id)


class TestReadOnlyGate:
    async def test_lapsed_mutation_blocked_with_402(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        await _force_lapse(cloud_app, user_id)
        resp = await cloud_client.post("/api/settings/board/reset")
        assert resp.status_code == 402
        assert resp.json()["error"] == "subscription_required"

    async def test_lapsed_reads_still_work(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        await _force_lapse(cloud_app, user_id)
        resp = await cloud_client.get("/api/billing/status")
        assert resp.status_code == 200
        assert resp.json()["read_only"] is True

    async def test_lapsed_can_still_checkout_and_logout(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        await _force_lapse(cloud_app, user_id)
        checkout = await cloud_client.post(
            "/api/billing/checkout", json={"plan": "monthly"}
        )
        assert checkout.status_code == 200
        logout = await cloud_client.post("/api/auth/logout")
        assert logout.status_code in (200, 204)

    async def test_trialing_mutations_pass(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.post("/api/settings/board/reset")
        assert resp.status_code == 200


class TestGrantsInFeatures:
    async def test_html_page_carries_cloud_grants(self, cloud_app, cloud_client):
        await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.get("/", follow_redirects=True)
        assert resp.status_code == 200
        assert '"cloud.autosync": true' in resp.text

    async def test_trial_banner_renders_for_trialing_user(
        self, cloud_app, cloud_client
    ):
        await signup_first_user(cloud_app, cloud_client)
        await cloud_client.post("/api/setup/complete")
        resp = await cloud_client.get("/", follow_redirects=True)
        assert "billing-banner--trial" in resp.text

    async def test_lapsed_banner_renders(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        await cloud_client.post("/api/setup/complete")
        await _force_lapse(cloud_app, user_id)
        resp = await cloud_client.get("/", follow_redirects=True)
        assert "billing-banner--lapsed" in resp.text

    async def test_lapsed_grants_are_false(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        await _force_lapse(cloud_app, user_id)
        resp = await cloud_client.get("/", follow_redirects=True)
        assert '"cloud.autosync": false' in resp.text

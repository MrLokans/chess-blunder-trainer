from tests.billing.conftest import signup_first_user


class TestCloudBootstrap:
    async def test_app_state_billing_set(self, cloud_app):
        assert cloud_app.state.billing is not None
        assert cloud_app.state.billing.db_path.name == "billing.sqlite3"

    async def test_cloud_off_leaves_billing_none(self, credentials_app):
        assert credentials_app.state.billing is None

    async def test_signup_starts_trial(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        sub = await cloud_app.state.billing.service.get_subscription(user_id)
        assert sub is not None
        assert sub.status.value == "trialing"

    async def test_account_deletion_removes_billing_rows(self, cloud_app, cloud_client):
        user_id = await signup_first_user(cloud_app, cloud_client)
        resp = await cloud_client.delete("/api/auth/account")
        assert resp.status_code in (200, 204)
        assert (await cloud_app.state.billing.service.get_subscription(user_id)) is None

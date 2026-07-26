import httpx
import pytest
from httpx import ASGITransport

from blunder_tutor import auth as auth_pkg
from blunder_tutor.auth import AuthDb
from blunder_tutor.billing.repository import SubscriptionRepository
from blunder_tutor.billing.schema import initialize_billing_schema
from tests.auth.conftest import (  # noqa: F401
    _booted_credentials_app,
    client_credentials_mode,
    credentials_app,
    invite_code,
)
from tests.billing.fakes import FakeStripeGateway

CLOUD_ENV = {
    "CLOUD_MODE": "true",
    "STRIPE_SECRET_KEY": "sk_test_x",
    "STRIPE_WEBHOOK_SECRET": "whsec_x",
    "STRIPE_PRICE_MONTHLY": "price_m",
    "STRIPE_PRICE_ANNUAL": "price_a",
    "PUBLIC_BASE_URL": "http://testserver",
}


@pytest.fixture
async def cloud_app(tmp_path, monkeypatch):
    for key, env_value in CLOUD_ENV.items():
        monkeypatch.setenv(key, env_value)
    monkeypatch.setattr(
        "blunder_tutor.web.app_lifecycle.build_stripe_gateway",
        lambda config: FakeStripeGateway(),
    )
    async with _booted_credentials_app(tmp_path, monkeypatch, max_users="2") as app:
        yield app


@pytest.fixture
async def cloud_client(cloud_app):
    transport = ASGITransport(app=cloud_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client


async def signup_first_user(cloud_app, client) -> str:
    invite = await cloud_app.state.auth.storage.setup.get(
        auth_pkg.INVITE_CODE_SETUP_KEY
    )
    resp = await client.post(
        "/api/auth/signup",
        json={
            "username": "alice",
            "password": "password123",
            "invite_code": invite,
        },
    )
    assert resp.status_code == 200, resp.text
    users = await cloud_app.state.auth.storage.users.list_all()
    return users[0].id


@pytest.fixture
async def billing_db(tmp_path):
    path = tmp_path / "billing.sqlite3"
    await initialize_billing_schema(path)
    db = AuthDb(path)
    await db.connect()
    yield db
    await db.close()


@pytest.fixture
async def repo(billing_db):
    return SubscriptionRepository(billing_db)

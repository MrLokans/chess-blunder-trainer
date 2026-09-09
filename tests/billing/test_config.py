import pytest
from pydantic import ValidationError

from blunder_tutor.web.config import (
    AppConfig,
    BillingConfig,
    EngineConfig,
    _build_billing_config,
)

CLOUD_ENV = {
    "CLOUD_MODE": "true",
    "STRIPE_SECRET_KEY": "sk_test_x",
    "STRIPE_WEBHOOK_SECRET": "whsec_x",
    "STRIPE_PRICE_MONTHLY": "price_m",
    "STRIPE_PRICE_ANNUAL": "price_a",
    "PUBLIC_BASE_URL": "https://cloud.example.com",
}


def make_app_config(**overrides) -> AppConfig:
    base = {
        "engine_path": "/fake/stockfish",
        "engine": EngineConfig(path="/fake/stockfish"),
    }
    return AppConfig(**{**base, **overrides})


class TestBillingConfigDefaults:
    def test_defaults_are_inert(self):
        config = BillingConfig()
        assert config.cloud_mode is False
        assert config.trial_days == 14
        assert config.node_id == "node-1"

    def test_cloud_mode_requires_stripe_settings(self):
        with pytest.raises(ValidationError, match="STRIPE_SECRET_KEY"):
            BillingConfig(cloud_mode=True)


class TestBuildBillingConfig:
    def test_full_cloud_env(self):
        config = _build_billing_config(CLOUD_ENV)
        assert config.cloud_mode is True
        assert config.stripe_price_annual == "price_a"
        assert config.public_base_url == "https://cloud.example.com"

    def test_empty_env_is_inert(self):
        assert _build_billing_config({}).cloud_mode is False

    @pytest.mark.parametrize(
        ("attr", "expected"),
        [("trial_days", 30), ("node_id", "node-2")],
    )
    def test_overrides(self, attr, expected):
        env = {**CLOUD_ENV, "TRIAL_DAYS": "30", "NODE_ID": "node-2"}
        config = _build_billing_config(env)
        assert getattr(config, attr) == expected


class TestAppConfigCrossValidation:
    def test_cloud_mode_requires_credentials_auth(self):
        billing = _build_billing_config(CLOUD_ENV)
        with pytest.raises(ValidationError, match="AUTH_MODE=credentials"):
            make_app_config(billing=billing)

    def test_cloud_off_with_none_auth_is_fine(self):
        config = make_app_config()
        assert config.billing.cloud_mode is False

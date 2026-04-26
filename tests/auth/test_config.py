from __future__ import annotations

import argparse
from types import MappingProxyType

import pytest

from blunder_tutor.web.config import (
    SECRET_KEY_MIN_LEN,
    AuthConfig,
    config_factory,
)

_VALID_SECRET = "x" * SECRET_KEY_MIN_LEN


def _args() -> argparse.Namespace:
    return argparse.Namespace(engine_path=None, depth=None)


def _base_env(**extra: str) -> dict[str, str]:
    return {"STOCKFISH_BINARY": "/fake/stockfish", **extra}


class TestAuthConfigDefaults:
    def test_default_mode_is_none(self):
        config = config_factory(_args(), _base_env())
        assert config.auth.mode == "none"
        assert config.auth.secret_key is None
        assert config.auth.max_users == 1
        assert config.auth.session_max_age_seconds == 60 * 60 * 24 * 30
        assert config.auth.session_idle_seconds == 60 * 60 * 24 * 7


class TestAuthConfigCredentialsMode:
    def test_happy_path(self):
        config = config_factory(
            _args(),
            _base_env(
                AUTH_MODE="credentials",
                SECRET_KEY=_VALID_SECRET,
                MAX_USERS="5",
            ),
        )
        assert config.auth.mode == "credentials"
        assert config.auth.secret_key == _VALID_SECRET
        assert config.auth.max_users == 5

    def test_requires_secret_key(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            config_factory(_args(), _base_env(AUTH_MODE="credentials"))

    def test_requires_min_secret_key_length(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            config_factory(
                _args(),
                _base_env(AUTH_MODE="credentials", SECRET_KEY="short"),
            )

    def test_accepts_secret_exactly_at_minimum(self):
        config = config_factory(
            _args(),
            _base_env(
                AUTH_MODE="credentials",
                SECRET_KEY="x" * SECRET_KEY_MIN_LEN,
            ),
        )
        assert config.auth.secret_key is not None
        assert len(config.auth.secret_key) == SECRET_KEY_MIN_LEN

    def test_rejects_secret_one_char_below_minimum(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY="x" * (SECRET_KEY_MIN_LEN - 1),
                ),
            )

    def test_requires_positive_max_users(self):
        with pytest.raises(ValueError, match="MAX_USERS"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    MAX_USERS="0",
                ),
            )

    def test_rejects_negative_max_users(self):
        with pytest.raises(ValueError, match="MAX_USERS"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    MAX_USERS="-1",
                ),
            )

    def test_rejects_non_integer_max_users(self):
        with pytest.raises(ValueError, match="MAX_USERS"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    MAX_USERS="abc",
                ),
            )

    def test_rejects_demo_mode_combo(self):
        with pytest.raises(ValueError, match="DEMO_MODE"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    DEMO_MODE="true",
                ),
            )

    def test_overrides_session_timeouts(self):
        config = config_factory(
            _args(),
            _base_env(
                AUTH_MODE="credentials",
                SECRET_KEY=_VALID_SECRET,
                SESSION_MAX_AGE_SECONDS="3600",
                SESSION_IDLE_SECONDS="600",
            ),
        )
        assert config.auth.session_max_age_seconds == 3600
        assert config.auth.session_idle_seconds == 600

    def test_rejects_zero_session_max_age(self):
        with pytest.raises(ValueError, match="SESSION_MAX_AGE_SECONDS"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    SESSION_MAX_AGE_SECONDS="0",
                ),
            )

    def test_rejects_idle_greater_than_max_age(self):
        with pytest.raises(ValueError, match="SESSION_IDLE_SECONDS"):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    SESSION_MAX_AGE_SECONDS="3600",
                    SESSION_IDLE_SECONDS="7200",
                ),
            )

    def test_allows_idle_equal_to_max_age(self):
        config = config_factory(
            _args(),
            _base_env(
                AUTH_MODE="credentials",
                SECRET_KEY=_VALID_SECRET,
                SESSION_MAX_AGE_SECONDS="3600",
                SESSION_IDLE_SECONDS="3600",
            ),
        )
        assert (
            config.auth.session_idle_seconds
            == config.auth.session_max_age_seconds
            == 3600
        )


class TestAuthModeParsing:
    @pytest.mark.parametrize("raw", ["", "none", "NONE", "None"])
    def test_none_variants(self, raw: str):
        config = config_factory(_args(), _base_env(AUTH_MODE=raw))
        assert config.auth.mode == "none"

    @pytest.mark.parametrize("raw", ["credentials", "CREDENTIALS", "Credentials"])
    def test_credentials_variants(self, raw: str):
        config = config_factory(
            _args(),
            _base_env(AUTH_MODE=raw, SECRET_KEY=_VALID_SECRET),
        )
        assert config.auth.mode == "credentials"

    @pytest.mark.parametrize("raw", ["oauth", "saml", "yes", "true"])
    def test_rejects_unknown_mode(self, raw: str):
        with pytest.raises(ValueError, match="AUTH_MODE"):
            config_factory(_args(), _base_env(AUTH_MODE=raw))


class TestNoneModeIgnoresCredentialsEnvVars:
    def test_secret_key_ignored_when_mode_none(self):
        config = config_factory(_args(), _base_env(SECRET_KEY="any-length-ok"))
        assert config.auth.mode == "none"
        assert config.auth.secret_key == "any-length-ok"

    def test_demo_mode_allowed_when_auth_none(self):
        config = config_factory(_args(), _base_env(DEMO_MODE="true"))
        assert config.auth.mode == "none"
        assert config.demo_mode is True


class TestEmptyEnvVarsFailLoudly:
    @pytest.mark.parametrize(
        "key",
        ["MAX_USERS", "SESSION_MAX_AGE_SECONDS", "SESSION_IDLE_SECONDS"],
    )
    def test_empty_string_raises(self, key: str):
        with pytest.raises(ValueError, match=key):
            config_factory(
                _args(),
                _base_env(
                    AUTH_MODE="credentials",
                    SECRET_KEY=_VALID_SECRET,
                    **{key: ""},
                ),
            )


class TestReadOnlyMappingCompat:
    def test_accepts_mapping_proxy(self):
        env = MappingProxyType(_base_env())
        config = config_factory(_args(), env)
        assert config.auth.mode == "none"


class TestAuthConfigDirectInstantiation:
    """Direct AuthConfig(...) construction (e.g. in tests or scripts) must also
    enforce invariants — validation lives on the model, not on the env parser."""

    def test_credentials_without_secret_key_rejected(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            AuthConfig(mode="credentials")

    def test_short_secret_key_rejected(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            AuthConfig(mode="credentials", secret_key="short")

    def test_idle_greater_than_max_rejected(self):
        with pytest.raises(ValueError, match="SESSION_IDLE_SECONDS"):
            AuthConfig(
                mode="credentials",
                secret_key=_VALID_SECRET,
                session_max_age_seconds=60,
                session_idle_seconds=120,
            )

    def test_none_mode_permits_missing_secret_key(self):
        config = AuthConfig(mode="none")
        assert config.secret_key is None

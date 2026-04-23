from __future__ import annotations

import argparse as _ap
import os as _os
from types import SimpleNamespace

import pytest

from blunder_tutor.web.api.auth import _cookie_secure
from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import AppConfig, AuthConfig, config_factory
from tests.helpers.engine import mock_engine_context


def _make_config(
    *,
    cookie_secure: bool | None = None,
    trust_proxy: bool = False,
    vite_dev: bool = False,
) -> AppConfig:
    return AppConfig(
        engine_path="/fake/sf",
        engine={"path": "/fake/sf"},  # type: ignore[arg-type]
        vite_dev=vite_dev,
        auth=AuthConfig(
            mode="credentials",
            secret_key="x" * 64,
            cookie_secure=cookie_secure,
            trust_proxy=trust_proxy,
        ),
    )


def _make_request(*, scheme: str = "http", headers: dict | None = None):
    return SimpleNamespace(
        url=SimpleNamespace(scheme=scheme),
        headers=(headers or {}),
    )


class TestCookieSecure:
    def test_explicit_true_wins(self):
        config = _make_config(cookie_secure=True)
        request = _make_request(scheme="http")
        assert _cookie_secure(config, request) is True

    def test_explicit_false_wins(self):
        config = _make_config(cookie_secure=False)
        request = _make_request(scheme="https")
        assert _cookie_secure(config, request) is False

    def test_https_scheme_yields_true(self):
        config = _make_config()
        request = _make_request(scheme="https")
        assert _cookie_secure(config, request) is True

    def test_forwarded_proto_honored_when_trust_proxy_true(self):
        config = _make_config(trust_proxy=True)
        request = _make_request(
            scheme="http", headers={"x-forwarded-proto": "https"}
        )
        assert _cookie_secure(config, request) is True

    def test_forwarded_proto_ignored_when_trust_proxy_false(self):
        """Direct-to-uvicorn deploy must NOT trust a client-supplied
        ``X-Forwarded-Proto`` header — an attacker could set the header
        to make the app think the connection was HTTPS and keep Secure
        on a cookie that's about to ride a plain-HTTP response."""
        config = _make_config(trust_proxy=False)
        request = _make_request(
            scheme="http", headers={"x-forwarded-proto": "https"}
        )
        assert _cookie_secure(config, request) is False

    def test_forwarded_proto_chain_uses_leftmost(self):
        """Reverse proxies that prepend their own scheme produce a
        comma-separated chain; the leftmost (original client) value
        wins."""
        config = _make_config(trust_proxy=True)
        request = _make_request(
            scheme="http",
            headers={"x-forwarded-proto": "https, http"},
        )
        assert _cookie_secure(config, request) is True

    def test_forwarded_proto_http_stays_false(self):
        config = _make_config(trust_proxy=True)
        request = _make_request(
            scheme="http", headers={"x-forwarded-proto": "http"}
        )
        assert _cookie_secure(config, request) is False

    def test_plain_http_no_proxy_falls_back_false(self):
        config = _make_config()
        request = _make_request(scheme="http")
        assert _cookie_secure(config, request) is False


class TestStartupWarning:
    """Boot-time nudge for the insecure default posture."""

    async def test_warning_emitted_when_neither_knob_set(
        self, tmp_path, monkeypatch, caplog: pytest.LogCaptureFixture
    ):
        monkeypatch.setenv("AUTH_MODE", "credentials")
        monkeypatch.setenv("SECRET_KEY", "x" * 64)
        monkeypatch.setenv("MAX_USERS", "1")
        monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
        monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
        monkeypatch.setenv("VITE_DEV", "true")
        # Neither AUTH_COOKIE_SECURE nor AUTH_TRUST_PROXY set.
        monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
        monkeypatch.delenv("AUTH_TRUST_PROXY", raising=False)

        caplog.set_level("WARNING", logger="blunder_tutor.web.app")

        ns = _ap.Namespace(engine_path="/fake/stockfish", depth=20)
        config = config_factory(ns, dict(_os.environ))

        with mock_engine_context():
            app = create_app(config)
            async with app.router.lifespan_context(app):
                pass

        assert any(
            "AUTH_COOKIE_SECURE" in r.message
            and "AUTH_TRUST_PROXY" in r.message
            for r in caplog.records
        ), [r.message for r in caplog.records]

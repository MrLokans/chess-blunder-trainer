from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi_throttle import RateLimiter
from httpx import ASGITransport

from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import config_factory
from tests.helpers.engine import mock_engine_context


@contextlib.asynccontextmanager
async def _low_limit_app(
    tmp_path: Path,
    monkeypatch,
    *,
    login_limit: str = "2",
    signup_limit: str = "2",
):
    """Credentials-mode app with a deliberately low rate limit so the
    test suite doesn't have to spend seconds on bcrypt to observe a 429.
    """
    monkeypatch.setenv("AUTH_MODE", "credentials")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("MAX_USERS", "1")
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    monkeypatch.setenv("VITE_DEV", "true")
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT", login_limit)
    monkeypatch.setenv("AUTH_LOGIN_RATE_WINDOW_SECONDS", "60")
    monkeypatch.setenv("AUTH_SIGNUP_RATE_LIMIT", signup_limit)
    monkeypatch.setenv("AUTH_SIGNUP_RATE_WINDOW_SECONDS", "3600")
    # Opt-in to `X-Forwarded-For` keying so the per-IP scoping test can
    # exercise the header. Prod deployments are expected to set this
    # only behind a trusted reverse proxy.
    monkeypatch.setenv("AUTH_TRUST_PROXY", "true")

    ns = argparse.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(os.environ))

    with mock_engine_context():
        app = create_app(config)
        async with app.router.lifespan_context(app):
            yield app


@pytest.fixture
async def low_rate_limit_client(tmp_path: Path, monkeypatch):
    async with _low_limit_app(tmp_path, monkeypatch) as app:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client, app


class TestLoginRateLimit:
    async def test_login_returns_429_after_limit_exceeded(
        self, low_rate_limit_client: tuple[httpx.AsyncClient, FastAPI]
    ):
        client, _app = low_rate_limit_client
        # limit=2: first two attempts are rejected on credentials (401),
        # the third trips the limiter (429) before bcrypt runs.
        for _ in range(2):
            r = await client.post(
                "/api/auth/login",
                json={"username": "ghost", "password": "password123"},
            )
            assert r.status_code == 401, r.text
        r = await client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "password123"},
        )
        assert r.status_code == 429, r.text

    async def test_login_limiter_scoped_per_ip(
        self, low_rate_limit_client: tuple[httpx.AsyncClient, FastAPI]
    ):
        client, _app = low_rate_limit_client
        for _ in range(2):
            await client.post(
                "/api/auth/login",
                json={"username": "ghost", "password": "password123"},
                headers={"x-forwarded-for": "10.0.0.1"},
            )
        r = await client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "password123"},
            headers={"x-forwarded-for": "10.0.0.1"},
        )
        assert r.status_code == 429, r.text

        # A different IP should still get a normal 401, not 429 — each IP
        # has its own bucket.
        r = await client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "password123"},
            headers={"x-forwarded-for": "10.0.0.2"},
        )
        assert r.status_code == 401, r.text


class TestTrustProxyDefault:
    async def test_default_deploy_ignores_spoofed_x_forwarded_for(
        self, tmp_path: Path, monkeypatch
    ):
        # `AUTH_TRUST_PROXY` left unset → direct-to-uvicorn posture. A
        # client rotating `X-Forwarded-For` across requests must NOT get
        # a fresh bucket per forged IP; the limiter must key on the
        # real client host (all from `testserver` in ASGITransport).
        monkeypatch.delenv("AUTH_TRUST_PROXY", raising=False)
        async with _low_limit_app(tmp_path, monkeypatch, login_limit="2") as app:
            # `_low_limit_app` sets AUTH_TRUST_PROXY=true above; override
            # by reconstructing the limiter here to simulate the real
            # default posture.
            app.state.login_rate_limiter = RateLimiter(
                times=2,
                seconds=60,
                trust_proxy=False,
                add_headers=True,
            )
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                for forged_ip in ("10.0.0.1", "10.0.0.2"):
                    await client.post(
                        "/api/auth/login",
                        json={
                            "username": "ghost",
                            "password": "password123",
                        },
                        headers={"x-forwarded-for": forged_ip},
                    )
                r = await client.post(
                    "/api/auth/login",
                    json={"username": "ghost", "password": "password123"},
                    headers={"x-forwarded-for": "10.0.0.99"},
                )
                assert r.status_code == 429, r.text


class TestSignupRateLimit:
    async def test_signup_returns_429_after_limit_exceeded(
        self, low_rate_limit_client: tuple[httpx.AsyncClient, FastAPI]
    ):
        client, _app = low_rate_limit_client
        for _ in range(2):
            r = await client.post(
                "/api/auth/signup",
                json={"username": "whoever", "password": "password123"},
            )
            # 403 invite_code_required — first-user signup without invite.
            # The point is the request reached the handler and consumed a
            # bucket slot; the status must be the specific "needs invite"
            # response so a regression that e.g. 400s on the payload does
            # not silently pass this test.
            assert r.status_code == 403, r.text
            assert r.json()["detail"] == "invite_code_required"
        r = await client.post(
            "/api/auth/signup",
            json={"username": "whoever", "password": "password123"},
        )
        assert r.status_code == 429, r.text


class TestFailedLoginLogged:
    async def test_failed_login_emits_warning(
        self,
        low_rate_limit_client: tuple[httpx.AsyncClient, FastAPI],
        caplog: pytest.LogCaptureFixture,
    ):
        client, _app = low_rate_limit_client
        caplog.set_level("WARNING", logger="blunder_tutor.web.api.auth")
        await client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "password123"},
        )
        assert any("auth.login.failed" in rec.message for rec in caplog.records), [
            r.message for r in caplog.records
        ]

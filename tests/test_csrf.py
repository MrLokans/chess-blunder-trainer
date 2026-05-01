from __future__ import annotations

import argparse as _ap
import os as _os
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import config_factory
from blunder_tutor.web.middleware import (
    _extract_host,
    _origin_matches_host,
)
from tests.helpers.engine import mock_engine_context


class TestExtractHost:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("http://example.com/path", "example.com"),
            ("https://example.com:8000/path", "example.com"),
            ("http://example.com", "example.com"),
            ("https://user:pass@example.com/", "example.com"),
            ("https://Example.COM/", "example.com"),
            ("no-scheme", None),
            ("", None),
        ],
    )
    def test_cases(self, url, expected):
        assert _extract_host(url) == expected


class _FakeRequest:
    """Minimal request stand-in for the pure-logic host test."""

    def __init__(self, headers):
        self.headers = headers


class TestOriginMatchesHost:
    def test_origin_matches(self):
        r = _FakeRequest({"origin": "http://example.com:8000", "host": "example.com"})
        assert _origin_matches_host(r) is True  # type: ignore[arg-type]

    def test_origin_mismatch_rejected(self):
        r = _FakeRequest({"origin": "https://evil.com", "host": "example.com"})
        assert _origin_matches_host(r) is False  # type: ignore[arg-type]

    def test_referer_fallback(self):
        r = _FakeRequest({"referer": "http://example.com/foo", "host": "example.com"})
        assert _origin_matches_host(r) is True  # type: ignore[arg-type]

    def test_referer_mismatch_rejected(self):
        r = _FakeRequest({"referer": "https://evil.com/foo", "host": "example.com"})
        assert _origin_matches_host(r) is False  # type: ignore[arg-type]

    def test_neither_header_allowed(self):
        r = _FakeRequest({"host": "example.com"})
        # Absent-both is the non-browser client path; SameSite=Lax on
        # the session cookie is the primary defense in that case.
        assert _origin_matches_host(r) is True  # type: ignore[arg-type]

    def test_case_insensitive_host(self):
        r = _FakeRequest({"origin": "http://EXAMPLE.com", "host": "Example.COM"})
        assert _origin_matches_host(r) is True  # type: ignore[arg-type]


@pytest.fixture
async def app_client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    monkeypatch.setenv("VITE_DEV", "true")
    monkeypatch.setenv("AUTH_MODE", "none")

    ns = _ap.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(_os.environ))

    with mock_engine_context():
        app = create_app(config)
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                yield client


class TestCsrfMiddleware:
    async def test_same_origin_post_allowed(self, app_client: httpx.AsyncClient):
        r = await app_client.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "whoever"},
            headers={"Origin": "http://testserver"},
        )
        # May 400 on content validation but MUST NOT be the CSRF 403.
        assert r.status_code != HTTPStatus.FORBIDDEN or r.json().get("error") != "csrf"

    async def test_cross_origin_post_rejected_with_csrf_403(
        self, app_client: httpx.AsyncClient
    ):
        r = await app_client.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "whoever"},
            headers={"Origin": "https://evil.com"},
        )
        assert r.status_code == HTTPStatus.FORBIDDEN
        assert r.json()["error"] == "csrf"

    async def test_get_requests_are_untouched(self, app_client: httpx.AsyncClient):
        r = await app_client.get("/health", headers={"Origin": "https://evil.com"})
        assert r.status_code == HTTPStatus.OK

    async def test_absent_headers_allowed_by_default(
        self, app_client: httpx.AsyncClient
    ):
        # Httpx doesn't set Origin — simulates CLI / programmatic access.
        r = await app_client.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "whoever"},
        )
        assert r.status_code != HTTPStatus.FORBIDDEN or r.json().get("error") != "csrf"


@pytest.fixture
async def host_pinned_client(tmp_path: Path, monkeypatch):
    """App booted with ALLOWED_HOSTS=trusted.example — proves that the
    TrustedHostMiddleware layer catches spoofed Host headers before
    CSRF even sees the request."""
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    monkeypatch.setenv("VITE_DEV", "true")
    monkeypatch.setenv("AUTH_MODE", "none")
    monkeypatch.setenv("ALLOWED_HOSTS", "trusted.example")

    ns = _ap.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(_os.environ))

    with mock_engine_context():
        app = create_app(config)
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://trusted.example"
            ) as client:
                yield client


class TestTrustedHostMiddleware:
    async def test_allowed_host_passes(self, host_pinned_client: httpx.AsyncClient):
        r = await host_pinned_client.get("/health")
        assert r.status_code == HTTPStatus.OK

    async def test_spoofed_host_rejected(self, host_pinned_client: httpx.AsyncClient):
        # Cross-origin attacker tries to pass Origin==Host by spoofing
        # the Host header. TrustedHostMiddleware returns 400 before
        # CsrfOriginMiddleware even runs.
        r = await host_pinned_client.get(
            "/health", headers={"host": "attacker.example"}
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST

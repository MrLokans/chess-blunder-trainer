from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from blunder_tutor.auth.types import SessionToken
from tests.auth.conftest import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    signup_via_http,
)


async def _session_row_exists(app: FastAPI, token: str) -> bool:
    return await app.state.auth.storage.sessions.get(SessionToken(token)) is not None


class TestLoginRotation:
    """OWASP V7 (Session Management): authentication MUST regenerate the
    session ID and MUST terminate the previous session at privilege
    change. The login route must therefore revoke whatever cookie the
    caller already holds before minting a fresh token."""

    async def test_login_revokes_pre_existing_session(
        self,
        credentials_app: FastAPI,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await signup_via_http(client_credentials_mode, invite_code)
        old_token = client_credentials_mode.cookies.get("session_token")
        assert old_token is not None
        assert await _session_row_exists(credentials_app, old_token)

        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        )
        assert r.status_code == 200
        new_token = client_credentials_mode.cookies.get("session_token")
        assert new_token is not None
        assert new_token != old_token

        assert not await _session_row_exists(credentials_app, old_token)
        assert await _session_row_exists(credentials_app, new_token)

    async def test_login_with_unknown_old_cookie_still_succeeds(
        self,
        credentials_app: FastAPI,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        """A garbage / already-revoked cookie must not crash the login
        path — revoking it is best-effort defense in depth."""
        await signup_via_http(client_credentials_mode, invite_code)
        await client_credentials_mode.post("/api/auth/logout")
        client_credentials_mode.cookies.clear()

        # Send a syntactically-plausible bogus cookie via a raw header
        # (sidesteps the jar so the response cookie can land cleanly).
        # The handler attempts a revoke that must no-op without raising.
        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
            headers={"Cookie": "session_token=" + "deadbeef" * 8},
        )
        assert r.status_code == 200
        new_token = r.cookies.get("session_token")
        assert new_token is not None
        assert await _session_row_exists(credentials_app, new_token)

    async def test_login_failure_does_not_revoke_existing_session(
        self,
        credentials_app: FastAPI,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        """A wrong-password POST must not log the caller out of their
        currently-valid session — revocation is tied to a successful
        privilege-change, not to an attempted one."""
        await signup_via_http(client_credentials_mode, invite_code)
        live_token = client_credentials_mode.cookies.get("session_token")
        assert live_token is not None

        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": DEFAULT_USERNAME, "password": "wrong-password"},
        )
        assert r.status_code == 401

        assert await _session_row_exists(credentials_app, live_token)


class TestSignupRotation:
    @pytest.fixture
    async def client_multi(self, credentials_app_multi: FastAPI):
        transport = httpx.ASGITransport(app=credentials_app_multi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client

    @pytest.fixture
    async def invite_multi(self, credentials_app_multi: FastAPI) -> str:
        code = await credentials_app_multi.state.auth.storage.setup.get("invite_code")
        assert code
        return code

    async def test_signup_revokes_pre_existing_session(
        self,
        credentials_app_multi: FastAPI,
        client_multi: httpx.AsyncClient,
        invite_multi: str,
    ):
        """A second signup from the same browser (MAX_USERS=2) must
        revoke the first user's cookie before issuing a new one — the
        cookie jar carries forward across users in this transport, and
        any pre-existing session is by-definition not the new user's."""
        await signup_via_http(client_multi, invite_multi, username="alice")
        old_token = client_multi.cookies.get("session_token")
        assert old_token is not None

        r = await client_multi.post(
            "/api/auth/signup",
            json={"username": "bob", "password": DEFAULT_PASSWORD},
        )
        assert r.status_code == 200
        new_token = client_multi.cookies.get("session_token")
        assert new_token is not None
        assert new_token != old_token

        assert not await _session_row_exists(credentials_app_multi, old_token)
        assert await _session_row_exists(credentials_app_multi, new_token)

    async def test_signup_failure_does_not_revoke_existing_session(
        self,
        credentials_app_multi: FastAPI,
        client_multi: httpx.AsyncClient,
        invite_multi: str,
    ):
        """Pin the helper-call ordering: ``_revoke_caller_cookie`` runs
        AFTER ``service.signup`` succeeds. A failed signup (e.g.
        duplicate username) must leave the caller's still-valid session
        intact."""
        await signup_via_http(client_multi, invite_multi, username="alice")
        live_token = client_multi.cookies.get("session_token")
        assert live_token is not None

        r = await client_multi.post(
            "/api/auth/signup",
            json={"username": "alice", "password": DEFAULT_PASSWORD},
        )
        assert r.status_code == 409

        assert await _session_row_exists(credentials_app_multi, live_token)

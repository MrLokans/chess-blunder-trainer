from __future__ import annotations

import httpx


class TestSignupCap:
    async def test_first_user_requires_invite_code(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={"username": "alice", "password": "password123"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "invite_code_required"

    async def test_first_user_with_bad_invite_rejected(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": "not-a-real-code",
            },
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "invite_code_invalid"

    async def test_first_user_with_valid_invite_succeeds(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 200
        assert r.json()["username"] == "alice"
        assert "session_token" in r.cookies

    async def test_invite_code_rotated_after_first_signup(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        # Same invite must not be replayable for a second account even if
        # MAX_USERS allowed it.
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "bob",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 403

    async def test_max_users_cap_blocks_second_signup(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        first = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert first.status_code == 200
        # MAX_USERS=1 (fixture default) → any subsequent signup 403s even
        # without an invite code.
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={"username": "bob", "password": "password123"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "user_cap_reached"

    async def test_signup_rejects_invalid_username(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "X",  # too short
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 400

    async def test_signup_rejects_short_password(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "short",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 400

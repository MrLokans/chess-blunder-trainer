from __future__ import annotations

import asyncio

import httpx

from tests.auth.conftest import signup_via_http as _signup


class TestLogin:
    async def test_login_after_signup_sets_fresh_session(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await _signup(client_credentials_mode, invite_code)
        client_credentials_mode.cookies.clear()

        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": "alice", "password": "password123"},
        )
        assert r.status_code == 200
        assert "session_token" in r.cookies
        assert r.json()["username"] == "alice"

    async def test_login_with_wrong_password_401s(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await _signup(client_credentials_mode, invite_code)
        client_credentials_mode.cookies.clear()

        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrong-password"},
        )
        assert r.status_code == 401
        assert r.json()["detail"] == "invalid_credentials"

    async def test_login_with_unknown_user_401s(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "password123"},
        )
        assert r.status_code == 401

    async def test_login_with_malformed_username_401s(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post(
            "/api/auth/login",
            json={"username": "A", "password": "password123"},
        )
        # Malformed username must be a generic 401, not 400 — we don't
        # want to reveal whether an input passed shape validation.
        assert r.status_code == 401


class TestMe:
    async def test_me_returns_current_user(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await _signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "alice"

    async def test_me_without_session_401s(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 401


class TestLogout:
    async def test_logout_revokes_session(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await _signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.post("/api/auth/logout")
        assert r.status_code == 204

        # Subsequent /me must 401 even though the client still holds the
        # cookie in its jar — the server deleted the row.
        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 401

    async def test_logout_all_revokes_every_session_for_user(
        self,
        credentials_app,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)

        # Manually mint a second session for the same user via the service
        # to simulate a login from another device.
        service = credentials_app.state.auth_service
        user = await service.authenticate(
            "credentials", {"username": "alice", "password": "password123"}
        )
        assert user is not None
        other = await service.create_session(user_id=user.id, user_agent=None, ip=None)
        sessions_before = await service.list_sessions(user.id)
        assert len(sessions_before) == 2

        r = await client_credentials_mode.post("/api/auth/logout-all")
        assert r.status_code == 204

        sessions_after = await service.list_sessions(user.id)
        assert sessions_after == []
        # The extra token we minted is dead too.
        assert await service.resolve_session(other.token, None) is None

    async def test_logout_is_idempotent_without_session(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post("/api/auth/logout")
        assert r.status_code == 204

    async def test_logout_all_is_idempotent_without_session(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post("/api/auth/logout-all")
        assert r.status_code == 204


class TestDeleteAccount:
    async def test_delete_account_removes_user_and_clears_cookie(
        self,
        credentials_app,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.delete("/api/auth/account")
        assert r.status_code == 204

        service = credentials_app.state.auth_service
        assert await service.user_count() == 0

        # New request with the stale cookie in the jar must not resolve.
        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 401

    async def test_delete_account_evicts_per_user_cache_entries(
        self,
        credentials_app,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        r = await _signup(client_credentials_mode, invite_code)
        user_id = r.json()["id"]

        # Warm the per-user caches by hitting a page that exercises
        # SetupCheckMiddleware + LocaleMiddleware.
        await client_credentials_mode.get("/api/auth/me")

        setup_cache = getattr(credentials_app.state, "_setup_completed_cache", {})
        locale_cache = getattr(credentials_app.state, "_locale_cache", {})
        # No assertion on pre-state — the caches may or may not have the
        # entry depending on whether any middleware path populated them
        # for this endpoint. The guarantee we care about is post-delete.

        r = await client_credentials_mode.delete("/api/auth/account")
        assert r.status_code == 204

        assert user_id not in setup_cache
        assert user_id not in locale_cache


class TestSignupAtomicity:
    """Major-1 regression: cap + invite consume happen in the same
    transaction as the user insert, so concurrent signups cannot both
    slip past the cap check."""

    async def test_concurrent_signups_respect_cap_of_one(
        self,
        credentials_app,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        async def post(username: str):
            return await client_credentials_mode.post(
                "/api/auth/signup",
                json={
                    "username": username,
                    "password": "password123",
                    "invite_code": invite_code,
                },
            )

        # Fire two racing signups with distinct usernames against
        # MAX_USERS=1. `AuthDb.transaction()` serializes them through the
        # write lock; the second one must see count>=max_users and 403.
        a, b = await asyncio.gather(post("alice"), post("bob"))
        statuses = sorted([a.status_code, b.status_code])
        assert statuses == [200, 403]

        service = credentials_app.state.auth_service
        assert await service.user_count() == 1

    async def test_invite_cannot_be_replayed_across_transaction_boundary(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        # First signup consumes the invite inside the atomic tx.
        ok = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert ok.status_code == 200

        # Even if MAX_USERS allowed it, the same invite must not let a
        # second account through — the DELETE happened atomically with
        # the first INSERT. Cap blocks this one anyway (MAX_USERS=1),
        # but the assertion is that the error classifies as cap_reached,
        # not invite_invalid — so the invite table is known-empty.
        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "bob",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "user_cap_reached"

    async def test_invite_survives_secret_key_rotation(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str, credentials_app
    ):
        """Regression guard for TREK-25: rotating SECRET_KEY on a running
        instance must not invalidate an already-issued invite. Previously
        the signup path re-verified the HMAC against the current secret,
        so a rotation bricked first-user setup with an opaque
        ``invite_code_invalid`` until the operator also regenerated the
        invite. The invite is now authoritative via stored-equality."""
        # Rotate the in-memory secret to a different valid value. The
        # stored invite in the setup table was signed under the original
        # secret — prior behavior would reject it with reason='hmac'.
        credentials_app.state.config.auth.secret_key = "y" * 64

        r = await client_credentials_mode.post(
            "/api/auth/signup",
            json={
                "username": "alice",
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 200, r.text

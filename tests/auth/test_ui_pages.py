from __future__ import annotations

import httpx

from tests.auth.conftest import signup_via_http as _signup


class TestLoginPage:
    async def test_renders_login_form_when_logged_out(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/login")
        assert r.status_code == 200
        assert "auth-root" in r.text
        assert "src/auth/login.tsx" in r.text

    async def test_redirects_to_home_when_already_authenticated(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.get("/login", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"


class TestSignupPage:
    async def test_redirects_to_setup_when_no_users_exist(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/signup", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/setup"

    async def test_renders_instance_full_page_when_cap_reached(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        # MAX_USERS=1 in the fixture — signing up once fills the instance.
        await _signup(client_credentials_mode, invite_code)
        client_credentials_mode.cookies.clear()

        r = await client_credentials_mode.get("/signup", follow_redirects=False)
        assert r.status_code == 403
        # Renders the signup_full template, not a JSON error page. The
        # user-cap message is the load-bearing copy.
        assert "text/html" in r.headers["content-type"]
        assert "auth-card" in r.text

    async def test_redirects_to_home_when_already_authenticated(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.get("/signup", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"


class TestSetupPage:
    async def test_renders_first_setup_when_no_users_exist(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/setup")
        assert r.status_code == 200
        assert "auth-root" in r.text
        assert "src/auth/first-setup.tsx" in r.text

    async def test_redirects_to_login_when_users_exist_but_unauthenticated(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)
        client_credentials_mode.cookies.clear()

        r = await client_credentials_mode.get("/setup", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"


class TestAuthLayoutBodyClass:
    """The `auth-layout` body class scopes the flex-center layout away from
    non-auth pages — an unscoped `body { display: flex; ... }` rule used to
    lay the demo banner and the auth card out side-by-side."""

    async def test_login_page_body_has_auth_layout_class(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/login")
        assert r.status_code == 200
        assert 'class="auth-layout"' in r.text

    async def test_setup_page_body_has_auth_layout_class(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.get("/setup")
        assert r.status_code == 200
        assert 'class="auth-layout"' in r.text

    async def test_signup_full_page_body_has_auth_layout_class(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)
        client_credentials_mode.cookies.clear()

        r = await client_credentials_mode.get("/signup", follow_redirects=False)
        assert r.status_code == 403
        assert 'class="auth-layout"' in r.text


class TestLogoutUi:
    async def test_post_logout_clears_session_and_redirects_to_login(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        await _signup(client_credentials_mode, invite_code)

        r = await client_credentials_mode.post("/logout", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"

        # Subsequent /api/auth/me must 401 — the server row is gone even
        # though the cookie jar may hold a stale value.
        r = await client_credentials_mode.get("/api/auth/me")
        assert r.status_code == 401

    async def test_post_logout_is_idempotent_without_session(
        self, client_credentials_mode: httpx.AsyncClient
    ):
        r = await client_credentials_mode.post("/logout", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"

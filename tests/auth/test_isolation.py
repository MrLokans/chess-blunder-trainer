from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import httpx
from fastapi import FastAPI
from httpx import ASGITransport

from blunder_tutor.repositories.settings import SettingsRepository


class TestUserDataIsolation:
    async def test_per_user_settings_persist_to_separate_databases(
        self, credentials_app_multi: FastAPI, tmp_path: Path
    ) -> None:
        """Two users writing the same setting key each end up in their
        own SQLite file under ``users_dir/<user_id>/main.sqlite3`` —
        there is no shared row either account could overwrite.

        This is the architectural invariant behind the whole
        credentials-mode design: identity is the DB path, and any
        regression that reintroduces a single shared DB would fail
        here on the ``alice_locale == "ru"`` / ``bob_locale == "pl"``
        assertions below.
        """
        invite_code = await credentials_app_multi.state.auth.storage.setup.get(
            "invite_code"
        )
        assert invite_code, "bootstrap should have seeded an invite code"

        transport = ASGITransport(app=credentials_app_multi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            r = await client.post(
                "/api/auth/signup",
                json={
                    "username": "alice",
                    "password": "password123",
                    "invite_code": invite_code,
                },
            )
            assert r.status_code == HTTPStatus.OK, r.text
            alice_id = r.json()["id"]

            r = await client.post("/api/settings/locale", json={"locale": "ru"})
            assert r.status_code == HTTPStatus.OK, r.text

            r = await client.post("/api/auth/logout")
            assert r.status_code == HTTPStatus.NO_CONTENT
            # Drop session_token + the locale cookie the POST set — a
            # stale cookie would make `_detect_locale` return "ru" for
            # bob even if his per-user DB is clean.
            client.cookies.clear()

            r = await client.post(
                "/api/auth/signup",
                json={"username": "bob", "password": "password123"},
            )
            assert r.status_code == HTTPStatus.OK, r.text
            bob_id = r.json()["id"]

            r = await client.post("/api/settings/locale", json={"locale": "pl"})
            assert r.status_code == HTTPStatus.OK, r.text

        assert alice_id != bob_id

        alice_db = tmp_path / "users" / alice_id / "main.sqlite3"
        bob_db = tmp_path / "users" / bob_id / "main.sqlite3"
        assert alice_db.exists()
        assert bob_db.exists()
        assert alice_db != bob_db

        alice_repo = SettingsRepository(db_path=alice_db)
        try:
            alice_locale = await alice_repo.get_setting("locale")
        finally:
            await alice_repo.close()

        bob_repo = SettingsRepository(db_path=bob_db)
        try:
            bob_locale = await bob_repo.get_setting("locale")
        finally:
            await bob_repo.close()

        assert alice_locale == "ru"
        assert bob_locale == "pl"

    async def test_user_b_signup_succeeds_without_invite_code(
        self, credentials_app_multi: FastAPI
    ) -> None:
        """Only the very first user needs the bootstrap invite code; a
        later signup (count >= 1) rejects any invite_code argument as
        noise but otherwise proceeds. Guards against a regression that
        would demand an invite on every signup and effectively lock
        multi-user instances out."""
        invite_code = await credentials_app_multi.state.auth.storage.setup.get(
            "invite_code"
        )
        assert invite_code

        transport = ASGITransport(app=credentials_app_multi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            r = await client.post(
                "/api/auth/signup",
                json={
                    "username": "alice",
                    "password": "password123",
                    "invite_code": invite_code,
                },
            )
            assert r.status_code == HTTPStatus.OK, r.text

            await client.post("/api/auth/logout")
            client.cookies.clear()

            r = await client.post(
                "/api/auth/signup",
                json={"username": "bob", "password": "password123"},
            )
            assert r.status_code == HTTPStatus.OK, r.text

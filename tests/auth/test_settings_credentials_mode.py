from __future__ import annotations

import httpx


class TestSettingsSaveInCredentialsMode:
    """Regression guards: settings handlers previously crashed with
    ``AttributeError: 'NoneType' object has no attribute 'update_jobs'``
    in credentials mode because ``app.state.scheduler`` is ``None`` when
    per-user scheduling is deferred. The handlers must gate the call on
    ``scheduler is not None`` so saving settings succeeds either way.
    """

    async def _signup(
        self,
        client: httpx.AsyncClient,
        invite_code: str,
        *,
        username: str = "alice",
    ) -> None:
        r = await client.post(
            "/api/auth/signup",
            json={
                "username": username,
                "password": "password123",
                "invite_code": invite_code,
            },
        )
        assert r.status_code == 200, r.text

    async def test_post_settings_returns_200_when_scheduler_is_none(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await self._signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.post(
            "/api/settings",
            json={
                "auto_sync": False,
                "sync_interval": 24,
                "max_games": 100,
                "auto_analyze": True,
                "spaced_repetition_days": 30,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"success": True}

    async def test_post_features_returns_200_when_scheduler_is_none(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        await self._signup(client_credentials_mode, invite_code)
        r = await client_credentials_mode.post(
            "/api/settings/features",
            json={"features": {"trainer.tactics": True}},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"success": True}

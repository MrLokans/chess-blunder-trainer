from __future__ import annotations

import httpx

from tests.auth.conftest import signup_via_http


class TestSettingsSaveInCredentialsMode:
    """End-to-end smoke for the settings POST path in credentials mode.

    Original premise (pre-TREK-38): the handler crashed with
    ``AttributeError: 'NoneType' has no attribute 'update_jobs'`` because
    ``app.state.scheduler`` was ``None`` in credentials mode and the
    handler called ``scheduler.update_jobs(settings)`` unconditionally.

    Post-TREK-38 the scheduler is never ``None`` and the handler no
    longer touches it at all — settings hot-reload is now a per-tick
    re-read in the fanout scheduler. These tests stay as cheap smoke
    coverage so the next attempt at scheduler-side hot-reload doesn't
    silently regress the 200-status contract.
    """

    async def test_post_settings_returns_200_in_credentials_mode(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        signup_response = await signup_via_http(client_credentials_mode, invite_code)
        assert signup_response.status_code == 200, signup_response.text
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

    async def test_post_features_returns_200_in_credentials_mode(
        self, client_credentials_mode: httpx.AsyncClient, invite_code: str
    ):
        signup_response = await signup_via_http(client_credentials_mode, invite_code)
        assert signup_response.status_code == 200, signup_response.text
        r = await client_credentials_mode.post(
            "/api/settings/features",
            json={"features": {"trainer.tactics": True}},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"success": True}

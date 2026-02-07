"""Tests for settings and stats API endpoints."""


def test_get_settings_returns_defaults(app):
    response = app.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    assert data["auto_sync"] is False
    assert data["sync_interval"] == 24
    assert data["max_games"] == 1000
    assert data["auto_analyze"] is True
    assert data["spaced_repetition_days"] == 30


def test_post_settings_persists_and_get_retrieves(app):
    # First save settings via POST
    response = app.post(
        "/api/settings",
        json={
            "lichess": "testuser",
            "chesscom": "",
            "auto_sync": True,
            "sync_interval": 6,
            "max_games": 2000,
            "auto_analyze": False,
            "spaced_repetition_days": 14,
        },
    )
    assert response.status_code == 200

    # Then retrieve via GET
    response = app.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    assert data["lichess_username"] == "testuser"
    assert data["auto_sync"] is True
    assert data["sync_interval"] == 6
    assert data["max_games"] == 2000
    assert data["auto_analyze"] is False
    assert data["spaced_repetition_days"] == 14


def test_get_features_returns_all_defaults_true(app):
    response = app.get("/api/settings/features")
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert data["features"]["page.dashboard"] is True
    assert data["features"]["trainer.tactics"] is True


def test_post_features_persists(app):
    response = app.post(
        "/api/settings/features",
        json={"features": {"page.dashboard": False, "trainer.threats": False}},
    )
    assert response.status_code == 200

    response = app.get("/api/settings/features")
    data = response.json()
    assert data["features"]["page.dashboard"] is False
    assert data["features"]["trainer.threats"] is False
    assert data["features"]["page.management"] is True


def test_post_features_toggle_back(app):
    app.post(
        "/api/settings/features",
        json={"features": {"dashboard.heatmap": False}},
    )
    app.post(
        "/api/settings/features",
        json={"features": {"dashboard.heatmap": True}},
    )
    response = app.get("/api/settings/features")
    assert response.json()["features"]["dashboard.heatmap"] is True

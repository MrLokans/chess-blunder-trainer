"""Tests for board settings API endpoints."""


def test_get_piece_sets(app):
    response = app.get("/api/settings/board/piece-sets")
    assert response.status_code == 200
    data = response.json()
    assert "piece_sets" in data
    assert len(data["piece_sets"]) > 0
    # Check wikipedia is included
    ids = [ps["id"] for ps in data["piece_sets"]]
    assert "wikipedia" in ids


def test_get_board_color_presets(app):
    response = app.get("/api/settings/board/color-presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) > 0
    # Check brown preset exists
    ids = [p["id"] for p in data["presets"]]
    assert "brown" in ids


def test_get_board_settings_defaults(app):
    response = app.get("/api/settings/board")
    assert response.status_code == 200
    data = response.json()
    assert data["piece_set"] == "wikipedia"
    assert data["board_light"] == "#f0d9b5"
    assert data["board_dark"] == "#b58863"


def test_update_board_settings(app):
    # Update settings
    response = app.post(
        "/api/settings/board",
        json={
            "piece_set": "cburnett",
            "board_light": "#dee3e6",
            "board_dark": "#8ca2ad",
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify they were saved
    response = app.get("/api/settings/board")
    assert response.status_code == 200
    data = response.json()
    assert data["piece_set"] == "cburnett"
    assert data["board_light"] == "#dee3e6"
    assert data["board_dark"] == "#8ca2ad"


def test_update_board_settings_invalid_piece_set(app):
    response = app.post(
        "/api/settings/board",
        json={"piece_set": "nonexistent"},
    )
    assert response.status_code == 400
    assert "Invalid piece set" in response.json()["detail"]


def test_update_board_settings_invalid_color(app):
    response = app.post(
        "/api/settings/board",
        json={"board_light": "not-a-color"},
    )
    assert response.status_code == 400
    assert "hex color" in response.json()["detail"]


def test_reset_board_settings(app):
    # First set custom values
    app.post(
        "/api/settings/board",
        json={"piece_set": "alpha", "board_light": "#eeeeee", "board_dark": "#333333"},
    )

    # Reset
    response = app.post("/api/settings/board/reset")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify defaults
    response = app.get("/api/settings/board")
    data = response.json()
    assert data["piece_set"] == "wikipedia"
    assert data["board_light"] == "#f0d9b5"
    assert data["board_dark"] == "#b58863"

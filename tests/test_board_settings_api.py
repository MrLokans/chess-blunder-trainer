import asyncio
from http import HTTPStatus

"""Tests for board settings API endpoints."""


def test_get_piece_sets(app):
    response = app.get("/api/settings/board/piece-sets")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "piece_sets" in data
    assert len(data["piece_sets"]) > 0
    ids = [ps["id"] for ps in data["piece_sets"]]
    assert "gioco" in ids


def test_get_board_color_presets(app):
    response = app.get("/api/settings/board/color-presets")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) > 0
    # Check brown preset exists
    ids = [p["id"] for p in data["presets"]]
    assert "brown" in ids


def test_get_board_settings_defaults(app):
    response = app.get("/api/settings/board")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["piece_set"] == "gioco"
    assert data["board_light"] is None
    assert data["board_dark"] is None


def test_explicit_null_clears_stored_board_colors(app):
    app.post(
        "/api/settings/board",
        json={"board_light": "#dee3e6", "board_dark": "#8ca2ad"},
    )
    assert app.get("/api/settings/board").json()["board_light"] == "#dee3e6"

    response = app.post(
        "/api/settings/board",
        json={"piece_set": "gioco", "board_light": None, "board_dark": None},
    )
    assert response.status_code == HTTPStatus.OK

    data = app.get("/api/settings/board").json()
    assert data["board_light"] is None
    assert data["board_dark"] is None


def test_omitted_field_leaves_stored_board_color_alone(app):
    app.post(
        "/api/settings/board",
        json={"board_light": "#dee3e6", "board_dark": "#8ca2ad"},
    )

    response = app.post("/api/settings/board", json={"piece_set": "merida"})
    assert response.status_code == HTTPStatus.OK

    data = app.get("/api/settings/board").json()
    assert data["piece_set"] == "merida"
    assert data["board_light"] == "#dee3e6"
    assert data["board_dark"] == "#8ca2ad"


def test_get_board_settings_discards_legacy_partial_or_invalid_colors(app):
    settings_repo = app.app.state.settings_repo
    asyncio.run(settings_repo.write_setting("board_light_color", "#GGGGGG"))
    asyncio.run(settings_repo.write_setting("board_dark_color", "#8ca2ad"))

    data = app.get("/api/settings/board").json()
    assert data["board_light"] is None
    assert data["board_dark"] is None


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
    assert response.status_code == HTTPStatus.OK
    assert response.json()["success"] is True

    # Verify they were saved
    response = app.get("/api/settings/board")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["piece_set"] == "cburnett"
    assert data["board_light"] == "#dee3e6"
    assert data["board_dark"] == "#8ca2ad"


def test_update_board_settings_invalid_piece_set(app):
    response = app.post(
        "/api/settings/board",
        json={"piece_set": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Invalid piece set" in response.json()["detail"]


def test_update_board_settings_invalid_color(app):
    response = app.post(
        "/api/settings/board",
        json={"board_light": "#GGGGGG", "board_dark": "#8ca2ad"},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "hex color" in response.json()["detail"]


def test_update_board_settings_rejects_partial_color_pair(app):
    response = app.post("/api/settings/board", json={"board_light": "#dee3e6"})
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "updated together" in response.json()["detail"]


def test_reset_board_settings(app):
    # First set custom values
    app.post(
        "/api/settings/board",
        json={"piece_set": "alpha", "board_light": "#eeeeee", "board_dark": "#333333"},
    )

    # Reset
    response = app.post("/api/settings/board/reset")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["success"] is True

    # Cleared back to the mode-aware default
    response = app.get("/api/settings/board")
    data = response.json()
    assert data["piece_set"] == "gioco"
    assert data["board_light"] is None
    assert data["board_dark"] is None

"""Tests for dashboard filter API endpoints (time control + game phase)."""


def test_blunders_by_phase_accepts_game_types(app):
    response = app.get(
        "/api/stats/blunders/by-phase?game_types=bullet&game_types=blitz"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_phase" in data


def test_blunders_by_phase_without_game_types(app):
    response = app.get("/api/stats/blunders/by-phase")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_blunders_by_eco_accepts_game_types(app):
    response = app.get(
        "/api/stats/blunders/by-eco?game_types=rapid&game_types=classical"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_opening" in data


def test_blunders_by_eco_without_game_types(app):
    response = app.get("/api/stats/blunders/by-eco")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_blunders_by_tactical_pattern_accepts_game_types(app):
    response = app.get(
        "/api/stats/blunders/by-tactical-pattern?game_types=bullet&game_types=blitz"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_pattern" in data


def test_blunders_by_tactical_pattern_without_game_types(app):
    response = app.get("/api/stats/blunders/by-tactical-pattern")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


# --- Game phase filter tests ---


def test_overview_accepts_game_phases(app):
    response = app.get("/api/stats?game_phases=opening&game_phases=middlegame")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_blunders_by_phase_accepts_game_phases(app):
    response = app.get("/api/stats/blunders/by-phase?game_phases=endgame")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_phase" in data


def test_blunders_by_color_accepts_game_phases(app):
    response = app.get(
        "/api/stats/blunders/by-color?game_phases=opening&game_phases=endgame"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_color" in data


def test_blunders_by_game_type_accepts_game_phases(app):
    response = app.get("/api/stats/blunders/by-game-type?game_phases=middlegame")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data
    assert "by_game_type" in data


def test_combined_game_type_and_phase_filters(app):
    response = app.get(
        "/api/stats?game_types=blitz&game_phases=opening&game_phases=middlegame"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_blunders_by_eco_accepts_game_phases(app):
    response = app.get("/api/stats/blunders/by-eco?game_phases=opening")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_blunders_by_difficulty_accepts_game_phases(app):
    response = app.get("/api/stats/blunders/by-difficulty?game_phases=endgame")
    assert response.status_code == 200
    data = response.json()
    assert "total_blunders" in data


def test_collapse_point_accepts_game_phases(app):
    response = app.get(
        "/api/stats/collapse-point?game_phases=middlegame&game_phases=endgame"
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_games_with_blunders" in data


def test_invalid_game_phase_ignored(app):
    response = app.get("/api/stats?game_phases=invalid_phase")
    assert response.status_code == 200

"""Tests for dashboard time control filter API endpoints."""


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

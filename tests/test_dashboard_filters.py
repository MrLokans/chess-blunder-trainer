"""Tests for dashboard filter API endpoints (time control + game phase)."""

from pathlib import Path

import pytest

from blunder_tutor.repositories.stats_repository import StatsRepository
from tests.helpers.stats_db import insert_test_game, insert_test_move

SMOKE_ENDPOINTS = [
    (
        "/api/stats/blunders/by-phase?game_types=bullet&game_types=blitz",
        ["total_blunders", "by_phase"],
    ),
    ("/api/stats/blunders/by-phase", ["total_blunders"]),
    (
        "/api/stats/blunders/by-eco?game_types=rapid&game_types=classical",
        ["total_blunders", "by_opening"],
    ),
    ("/api/stats/blunders/by-eco", ["total_blunders"]),
    (
        "/api/stats/blunders/by-tactical-pattern?game_types=bullet&game_types=blitz",
        ["total_blunders", "by_pattern"],
    ),
    ("/api/stats/blunders/by-tactical-pattern", ["total_blunders"]),
    ("/api/stats?game_phases=opening&game_phases=middlegame", ["total_blunders"]),
    (
        "/api/stats/blunders/by-phase?game_phases=endgame",
        ["total_blunders", "by_phase"],
    ),
    (
        "/api/stats/blunders/by-color?game_phases=opening&game_phases=endgame",
        ["total_blunders", "by_color"],
    ),
    (
        "/api/stats/blunders/by-game-type?game_phases=middlegame",
        ["total_blunders", "by_game_type"],
    ),
    (
        "/api/stats?game_types=blitz&game_phases=opening&game_phases=middlegame",
        ["total_blunders"],
    ),
    ("/api/stats/blunders/by-eco?game_phases=opening", ["total_blunders"]),
    ("/api/stats/blunders/by-difficulty?game_phases=endgame", ["total_blunders"]),
    (
        "/api/stats/collapse-point?game_phases=middlegame&game_phases=endgame",
        ["total_games_with_blunders"],
    ),
    ("/api/stats?game_phases=invalid_phase", []),
]


@pytest.mark.parametrize("url,expected_keys", SMOKE_ENDPOINTS)
def test_filter_endpoint_returns_200_with_expected_keys(app, url, expected_keys):
    response = app.get(url)
    assert response.status_code == 200
    data = response.json()
    for key in expected_keys:
        assert key in data


@pytest.fixture
async def stats_repo(db_path: Path):
    repo = StatsRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def seeded_db(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opp1")
    await insert_test_move(stats_repo, "g1", 5, 0, classification=3, move_number=3)
    await insert_test_game(
        stats_repo, "g2", "testuser", "testuser", "opp2", time_control="60+0"
    )
    await insert_test_move(stats_repo, "g2", 9, 0, classification=3, move_number=5)
    return stats_repo


async def test_blunders_by_phase_with_data(app, seeded_db):
    response = app.get("/api/stats/blunders/by-phase")
    assert response.status_code == 200
    data = response.json()
    assert data["total_blunders"] >= 1


async def test_game_type_filter_narrows_results(app, seeded_db):
    all_resp = app.get("/api/stats")
    bullet_resp = app.get("/api/stats?game_types=bullet")
    assert all_resp.status_code == 200
    assert bullet_resp.status_code == 200
    all_data = all_resp.json()
    bullet_data = bullet_resp.json()
    assert all_data["total_blunders"] >= bullet_data["total_blunders"]

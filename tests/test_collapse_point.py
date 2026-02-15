"""Tests for collapse point (critical moment) statistics."""

from __future__ import annotations

import pytest

from blunder_tutor.repositories.stats_repository import StatsFilter, StatsRepository
from blunder_tutor.utils.time_control import GAME_TYPE_FROM_STRING
from tests.helpers.stats_db import insert_test_game, insert_test_move


@pytest.fixture
async def stats_repo(db_path):
    repo = StatsRepository(db_path)
    yield repo
    await repo.close()


async def test_no_username_returns_empty(stats_repo):
    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] is None
    assert result["median_collapse_move"] is None
    assert result["distribution"] == []
    assert result["total_games_with_blunders"] == 0
    assert result["total_games_without_blunders"] == 0


async def test_single_game_single_blunder(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opponent")
    await insert_test_move(stats_repo, "g1", 1, 0, classification=0)
    await insert_test_move(stats_repo, "g1", 3, 0, classification=3, move_number=2)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] == 2
    assert result["median_collapse_move"] == 2
    assert result["total_games_with_blunders"] == 1
    assert len(result["distribution"]) == 1
    assert result["distribution"][0]["move_range"] == "1-5"
    assert result["distribution"][0]["count"] == 1


async def test_multiple_blunders_takes_first(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opponent")
    await insert_test_move(stats_repo, "g1", 19, 0, classification=3, move_number=10)
    await insert_test_move(stats_repo, "g1", 39, 0, classification=3, move_number=20)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] == 10
    assert result["total_games_with_blunders"] == 1


async def test_multiple_games_average(stats_repo):
    # Game 1: first blunder at move 10
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opp1")
    await insert_test_move(stats_repo, "g1", 19, 0, classification=3, move_number=10)

    # Game 2: first blunder at move 30
    await insert_test_game(stats_repo, "g2", "testuser", "testuser", "opp2")
    await insert_test_move(stats_repo, "g2", 59, 0, classification=3, move_number=30)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] == 20
    assert result["median_collapse_move"] == 20
    assert result["total_games_with_blunders"] == 2


async def test_clean_games_counted(stats_repo):
    # Game with blunder
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opp1")
    await insert_test_move(stats_repo, "g1", 19, 0, classification=3, move_number=10)

    # Game without blunder
    await insert_test_game(stats_repo, "g2", "testuser", "testuser", "opp2")
    await insert_test_move(stats_repo, "g2", 1, 0, classification=0)

    result = await stats_repo.get_collapse_point()
    assert result["total_games_with_blunders"] == 1
    assert result["total_games_without_blunders"] == 1


async def test_only_user_blunders_counted(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opponent")
    # Opponent blunder at move 5 (player=1 is black)
    await insert_test_move(stats_repo, "g1", 10, 1, classification=3, move_number=5)
    # User blunder at move 15
    await insert_test_move(stats_repo, "g1", 29, 0, classification=3, move_number=15)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] == 15


async def test_black_player_blunders(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "opponent", "testuser")
    await insert_test_move(stats_repo, "g1", 20, 1, classification=3, move_number=10)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] == 10
    assert result["total_games_with_blunders"] == 1


async def test_distribution_buckets(stats_repo):
    # Game 1: blunder at move 3 -> bucket 1-5
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "o1")
    await insert_test_move(stats_repo, "g1", 5, 0, classification=3, move_number=3)

    # Game 2: blunder at move 8 -> bucket 6-10
    await insert_test_game(stats_repo, "g2", "testuser", "testuser", "o2")
    await insert_test_move(stats_repo, "g2", 15, 0, classification=3, move_number=8)

    # Game 3: blunder at move 42 -> bucket 41+
    await insert_test_game(stats_repo, "g3", "testuser", "testuser", "o3")
    await insert_test_move(stats_repo, "g3", 83, 0, classification=3, move_number=42)

    result = await stats_repo.get_collapse_point()
    dist = {d["move_range"]: d["count"] for d in result["distribution"]}
    assert dist["1-5"] == 1
    assert dist["6-10"] == 1
    assert dist["41+"] == 1


async def test_game_type_filter(stats_repo):
    # Bullet game with blunder at move 5
    await insert_test_game(
        stats_repo, "g1", "testuser", "testuser", "o1", time_control="60+0"
    )
    await insert_test_move(stats_repo, "g1", 9, 0, classification=3, move_number=5)

    # Rapid game with blunder at move 25
    await insert_test_game(
        stats_repo, "g2", "testuser", "testuser", "o2", time_control="600+0"
    )
    await insert_test_move(stats_repo, "g2", 49, 0, classification=3, move_number=25)

    bullet_id = GAME_TYPE_FROM_STRING["bullet"]
    result = await stats_repo.get_collapse_point(
        filters=StatsFilter(game_types=[bullet_id])
    )
    assert result["avg_collapse_move"] == 5
    assert result["total_games_with_blunders"] == 1


async def test_no_blunders_at_all(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opponent")
    await insert_test_move(stats_repo, "g1", 1, 0, classification=0)

    result = await stats_repo.get_collapse_point()
    assert result["avg_collapse_move"] is None
    assert result["median_collapse_move"] is None
    assert result["total_games_with_blunders"] == 0
    assert result["total_games_without_blunders"] == 1


def test_api_endpoint_returns_200(app):
    response = app.get("/api/stats/collapse-point")
    assert response.status_code == 200
    data = response.json()
    assert "avg_collapse_move" in data
    assert "median_collapse_move" in data
    assert "distribution" in data
    assert "total_games_with_blunders" in data
    assert "total_games_without_blunders" in data


def test_api_endpoint_accepts_game_types(app):
    response = app.get("/api/stats/collapse-point?game_types=bullet&game_types=blitz")
    assert response.status_code == 200


def test_api_endpoint_accepts_date_filters(app):
    response = app.get(
        "/api/stats/collapse-point?start_date=2025-01-01&end_date=2025-12-31"
    )
    assert response.status_code == 200

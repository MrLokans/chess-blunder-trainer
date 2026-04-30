"""Tests for conversion & resilience stats."""

from __future__ import annotations

from http import HTTPStatus
import pytest

from blunder_tutor.repositories.stats_repository import StatsFilter, StatsRepository
from blunder_tutor.utils.time_control import GAME_TYPE_FROM_STRING
from tests.helpers.stats_db import insert_test_game, insert_test_move


@pytest.fixture
async def stats_repo(db_path):
    repo = StatsRepository(db_path)
    yield repo
    await repo.close()


async def test_no_username_returns_zeros(stats_repo):
    result = await stats_repo.get_conversion_resilience()
    assert result["conversion_rate"] == 0.0
    assert result["resilience_rate"] == 0.0
    assert result["games_with_advantage"] == 0


async def test_conversion_win_from_winning_position(stats_repo):
    await insert_test_game(stats_repo, "g1", "testuser", "testuser", "opponent", "1-0")
    await insert_test_move(
        stats_repo, "g1", 1, 0, eval_before=300
    )  # +3.0 from white's perspective

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1
    assert result["conversion_rate"] == 100.0


async def test_conversion_loss_from_winning_position(stats_repo):
    await insert_test_game(stats_repo, "g2", "testuser", "testuser", "opponent", "0-1")
    await insert_test_move(stats_repo, "g2", 1, 0, eval_before=500)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 0
    assert result["conversion_rate"] == 0.0


async def test_resilience_save_from_losing_position(stats_repo):
    await insert_test_game(
        stats_repo, "g3", "testuser", "testuser", "opponent", "1/2-1/2"
    )
    await insert_test_move(stats_repo, "g3", 1, 0, eval_before=-400)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1
    assert result["resilience_rate"] == 100.0


async def test_resilience_loss_from_losing_position(stats_repo):
    await insert_test_game(stats_repo, "g4", "testuser", "testuser", "opponent", "0-1")
    await insert_test_move(stats_repo, "g4", 1, 0, eval_before=-400)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 0
    assert result["resilience_rate"] == 0.0


async def test_black_perspective_eval_flipped(stats_repo):
    # User plays black, eval_before = +300 from white's POV = -300 from user's POV (losing)
    await insert_test_game(
        stats_repo, "g5", "testuser", "opponent", "testuser", "1/2-1/2"
    )
    await insert_test_move(
        stats_repo, "g5", 2, 1, eval_before=300
    )  # +3.0 from white's POV

    result = await stats_repo.get_conversion_resilience()
    # From user (black) perspective, eval = -300, so this is a losing position
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1
    assert result["games_with_advantage"] == 0


async def test_game_both_winning_and_losing(stats_repo):
    await insert_test_game(stats_repo, "g6", "testuser", "testuser", "opponent", "1-0")
    await insert_test_move(stats_repo, "g6", 1, 0, eval_before=500)  # winning
    await insert_test_move(stats_repo, "g6", 3, 0, eval_before=-400)  # losing

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1  # won from losing position


async def test_game_type_filter(stats_repo):
    await insert_test_game(
        stats_repo, "g7", "testuser", "testuser", "opponent", "1-0", "60+0"
    )  # bullet
    await insert_test_move(stats_repo, "g7", 1, 0, eval_before=500)

    await insert_test_game(
        stats_repo, "g8", "testuser", "testuser", "opponent", "0-1", "300+0"
    )  # blitz
    await insert_test_move(stats_repo, "g8", 1, 0, eval_before=500)

    bullet_id = GAME_TYPE_FROM_STRING["bullet"]
    result = await stats_repo.get_conversion_resilience(
        filters=StatsFilter(game_types=[bullet_id])
    )
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1


async def test_no_qualifying_positions(stats_repo):
    await insert_test_game(stats_repo, "g9", "testuser", "testuser", "opponent", "1-0")
    await insert_test_move(
        stats_repo, "g9", 1, 0, eval_before=100
    )  # only +1.0, below threshold

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 0
    assert result["games_with_disadvantage"] == 0
    assert result["conversion_rate"] == 0.0
    assert result["resilience_rate"] == 0.0


def test_api_endpoint_returns_200(app):
    response = app.get("/api/stats/conversion-resilience")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "conversion_rate" in data
    assert "resilience_rate" in data
    assert "games_with_advantage" in data
    assert "games_converted" in data
    assert "games_with_disadvantage" in data
    assert "games_saved" in data


def test_api_endpoint_accepts_game_types(app):
    response = app.get(
        "/api/stats/conversion-resilience?game_types=bullet&game_types=blitz"
    )
    assert response.status_code == HTTPStatus.OK

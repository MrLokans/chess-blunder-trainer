"""Tests for conversion & resilience stats."""

from __future__ import annotations

import pytest

from blunder_tutor.repositories.stats_repository import StatsRepository


@pytest.fixture
async def stats_repo(db_path):
    repo = StatsRepository(db_path)
    yield repo
    await repo.close()


async def _insert_game(
    stats_repo, game_id, username, white, black, result, time_control="300+0"
):
    from blunder_tutor.utils.time_control import classify_game_type

    game_type = int(classify_game_type(time_control))
    conn = await stats_repo.get_connection()
    await conn.execute(
        """
        INSERT INTO game_index_cache
            (game_id, source, username, white, black, result, time_control,
             end_time_utc, pgn_content, analyzed, indexed_at, game_type)
        VALUES (?, 'lichess', ?, ?, ?, ?, ?, '2025-01-15T10:00:00Z', '', 1, '2025-01-15T10:00:00Z', ?)
        """,
        (game_id, username, white, black, result, time_control, game_type),
    )
    await conn.execute(
        """
        INSERT INTO analysis_games (game_id, pgn_path, analyzed_at, engine_path, depth, time_limit,
                                    inaccuracy, mistake, blunder)
        VALUES (?, '', '2025-01-15', '', 20, 1.0, 0, 0, 0)
        """,
        (game_id,),
    )
    await conn.commit()


async def _insert_move(stats_repo, game_id, ply, player, eval_before, eval_after=0):
    conn = await stats_repo.get_connection()
    await conn.execute(
        """
        INSERT INTO analysis_moves
            (game_id, ply, move_number, player, uci, san, eval_before, eval_after,
             delta, cp_loss, classification)
        VALUES (?, ?, ?, ?, 'e2e4', 'e4', ?, ?, 0, 0, 0)
        """,
        (game_id, ply, (ply + 1) // 2, player, eval_before, eval_after),
    )
    await conn.commit()


async def test_no_username_returns_zeros(stats_repo):
    result = await stats_repo.get_conversion_resilience()
    assert result["conversion_rate"] == 0.0
    assert result["resilience_rate"] == 0.0
    assert result["games_with_advantage"] == 0


async def test_conversion_win_from_winning_position(stats_repo):
    await _insert_game(stats_repo, "g1", "testuser", "testuser", "opponent", "1-0")
    await _insert_move(stats_repo, "g1", 1, 0, 300)  # +3.0 from white's perspective

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1
    assert result["conversion_rate"] == 100.0


async def test_conversion_loss_from_winning_position(stats_repo):
    await _insert_game(stats_repo, "g2", "testuser", "testuser", "opponent", "0-1")
    await _insert_move(stats_repo, "g2", 1, 0, 500)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 0
    assert result["conversion_rate"] == 0.0


async def test_resilience_save_from_losing_position(stats_repo):
    await _insert_game(stats_repo, "g3", "testuser", "testuser", "opponent", "1/2-1/2")
    await _insert_move(stats_repo, "g3", 1, 0, -400)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1
    assert result["resilience_rate"] == 100.0


async def test_resilience_loss_from_losing_position(stats_repo):
    await _insert_game(stats_repo, "g4", "testuser", "testuser", "opponent", "0-1")
    await _insert_move(stats_repo, "g4", 1, 0, -400)

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 0
    assert result["resilience_rate"] == 0.0


async def test_black_perspective_eval_flipped(stats_repo):
    # User plays black, eval_before = +300 from white's POV = -300 from user's POV (losing)
    await _insert_game(stats_repo, "g5", "testuser", "opponent", "testuser", "1/2-1/2")
    await _insert_move(stats_repo, "g5", 2, 1, 300)  # +3.0 from white's POV

    result = await stats_repo.get_conversion_resilience()
    # From user (black) perspective, eval = -300, so this is a losing position
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1
    assert result["games_with_advantage"] == 0


async def test_game_both_winning_and_losing(stats_repo):
    await _insert_game(stats_repo, "g6", "testuser", "testuser", "opponent", "1-0")
    await _insert_move(stats_repo, "g6", 1, 0, 500)  # winning
    await _insert_move(stats_repo, "g6", 3, 0, -400)  # losing

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1
    assert result["games_with_disadvantage"] == 1
    assert result["games_saved"] == 1  # won from losing position


async def test_game_type_filter(stats_repo):
    await _insert_game(
        stats_repo, "g7", "testuser", "testuser", "opponent", "1-0", "60+0"
    )  # bullet
    await _insert_move(stats_repo, "g7", 1, 0, 500)

    await _insert_game(
        stats_repo, "g8", "testuser", "testuser", "opponent", "0-1", "300+0"
    )  # blitz
    await _insert_move(stats_repo, "g8", 1, 0, 500)

    from blunder_tutor.utils.time_control import GAME_TYPE_FROM_STRING

    bullet_id = GAME_TYPE_FROM_STRING["bullet"]
    result = await stats_repo.get_conversion_resilience(game_types=[bullet_id])
    assert result["games_with_advantage"] == 1
    assert result["games_converted"] == 1


async def test_no_qualifying_positions(stats_repo):
    await _insert_game(stats_repo, "g9", "testuser", "testuser", "opponent", "1-0")
    await _insert_move(stats_repo, "g9", 1, 0, 100)  # only +1.0, below threshold

    result = await stats_repo.get_conversion_resilience()
    assert result["games_with_advantage"] == 0
    assert result["games_with_disadvantage"] == 0
    assert result["conversion_rate"] == 0.0
    assert result["resilience_rate"] == 0.0


def test_api_endpoint_returns_200(app):
    response = app.get("/api/stats/conversion-resilience")
    assert response.status_code == 200
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
    assert response.status_code == 200

"""Shared helpers for inserting test data into stats-related DB tables."""

from __future__ import annotations

from blunder_tutor.repositories.stats_repository import StatsRepository
from blunder_tutor.utils.time_control import classify_game_type


async def insert_test_game(
    stats_repo: StatsRepository,
    game_id: str,
    username: str,
    white: str,
    black: str,
    result: str = "1-0",
    time_control: str = "300+0",
    end_time_utc: str = "2025-01-15T10:00:00Z",
    eco_code: str | None = None,
    eco_name: str | None = None,
) -> None:
    game_type = int(classify_game_type(time_control))
    conn = await stats_repo.get_connection()
    await conn.execute(
        """
        INSERT INTO game_index_cache
            (game_id, source, username, white, black, result, time_control,
             end_time_utc, pgn_content, analyzed, indexed_at, game_type)
        VALUES (?, 'lichess', ?, ?, ?, ?, ?, ?, '', 1, '2025-01-15T10:00:00Z', ?)
        """,
        (
            game_id,
            username,
            white,
            black,
            result,
            time_control,
            end_time_utc,
            game_type,
        ),
    )
    await conn.execute(
        """
        INSERT INTO analysis_games (game_id, pgn_path, analyzed_at, engine_path, depth, time_limit,
                                    inaccuracy, mistake, blunder, eco_code, eco_name)
        VALUES (?, '', '2025-01-15', '', 20, 1.0, 0, 0, 0, ?, ?)
        """,
        (game_id, eco_code, eco_name),
    )
    await conn.commit()


async def insert_test_move(
    stats_repo: StatsRepository,
    game_id: str,
    ply: int,
    player: int,
    *,
    classification: int = 0,
    move_number: int | None = None,
    eval_before: int = 0,
    eval_after: int = 0,
    cp_loss: int = 100,
    game_phase: int | None = None,
    tactical_pattern: int | None = None,
    difficulty: int | None = None,
) -> None:
    if move_number is None:
        move_number = (ply + 1) // 2
    conn = await stats_repo.get_connection()
    await conn.execute(
        """
        INSERT INTO analysis_moves
            (game_id, ply, move_number, player, uci, san, eval_before, eval_after,
             delta, cp_loss, classification, game_phase, tactical_pattern, difficulty)
        VALUES (?, ?, ?, ?, 'e2e4', 'e4', ?, ?, 0, ?, ?, ?, ?, ?)
        """,
        (
            game_id,
            ply,
            move_number,
            player,
            eval_before,
            eval_after,
            cp_loss,
            classification,
            game_phase,
            tactical_pattern,
            difficulty,
        ),
    )
    await conn.commit()

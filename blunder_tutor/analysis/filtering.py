from __future__ import annotations

from collections.abc import Iterable

from blunder_tutor.constants import (
    ALREADY_LOST_THRESHOLD,
    MATE_THRESHOLD,
    STILL_WINNING_THRESHOLD,
)


def is_valid_blunder(blunder: dict[str, object]) -> bool:
    eval_before = int(blunder.get("eval_before", 0))
    eval_after = int(blunder.get("eval_after", 0))

    if eval_before >= MATE_THRESHOLD and eval_after >= 0:
        return False

    if eval_after >= MATE_THRESHOLD:
        return False

    if eval_before <= ALREADY_LOST_THRESHOLD:
        return False

    return not eval_after >= STILL_WINNING_THRESHOLD


def filter_blunders(
    blunders: Iterable[dict[str, object]],
    game_side_map: dict[str, int],
) -> list[dict[str, object]]:
    filtered = []
    for blunder in blunders:
        game_id = str(blunder.get("game_id"))
        player = blunder.get("player")
        if (
            game_id in game_side_map
            and player == game_side_map[game_id]
            and is_valid_blunder(blunder)
        ):
            filtered.append(blunder)
    return filtered

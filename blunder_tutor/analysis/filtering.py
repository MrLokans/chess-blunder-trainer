"""Filtering logic for blunders and game analysis."""

from __future__ import annotations

from collections.abc import Iterable

from blunder_tutor.constants import MATE_THRESHOLD


def is_valid_blunder(blunder: dict[str, object]) -> bool:
    """Check if a blunder is valid (not a false positive).

    Args:
        blunder: Blunder record with eval_before and eval_after

    Returns:
        True if this is a real blunder, False if it's a false positive
    """
    eval_before = int(blunder.get("eval_before", 0))
    eval_after = int(blunder.get("eval_after", 0))

    # Skip if this looks like a checkmate delivery or mate-in-X situation
    # (eval_before is mate score ~100000 and eval_after dropped but still winning)
    if eval_before >= MATE_THRESHOLD and eval_after >= 0:
        return False  # Not a real blunder - was delivering mate or had forced mate

    # Skip if eval_after is still a winning mate (just a slower mate)
    return not eval_after >= MATE_THRESHOLD


def filter_blunders(
    blunders: Iterable[dict[str, object]],
    game_side_map: dict[str, int],
) -> list[dict[str, object]]:
    """Filter blunders to only include those by the player.

    Args:
        blunders: Iterable of blunder records
        game_side_map: Mapping of game_id -> player side (0=white, 1=black)

    Returns:
        List of filtered blunder records
    """
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

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess

from blunder_tutor.constants import DEFAULT_FIXTURES_PATH


@dataclass(frozen=True)
class TrapDefinition:
    id: str
    name: str
    category: str
    rating_range: tuple[int, int]
    victim_side: str
    entry_san_variants: list[list[str]]
    trap_san_variants: list[list[str]]
    mistake_ply: int
    mistake_san: str
    refutation_pgn: str
    refutation_move: str
    refutation_note: str
    recognition_tip: str
    tags: list[str]


@dataclass(frozen=True)
class TrapMatch:
    trap_id: str
    match_type: str  # "entered", "sprung", "executed"
    user_was_victim: bool
    mistake_ply: int | None


def _parse_pgn_to_san(pgn_str: str) -> list[str]:
    parts = pgn_str.split()
    moves = []
    for part in parts:
        if part.endswith("."):
            continue
        if part[0].isdigit() and "." in part:
            part = part.split(".")[-1]
            if part:
                moves.append(part)
        else:
            moves.append(part)
    return moves


def _game_san_sequence(game_board: chess.Board) -> list[str]:
    moves = []
    temp = game_board.root()
    for move in game_board.move_stack:
        try:
            san = temp.san(move)
        except (AssertionError, ValueError):
            break
        moves.append(san)
        temp.push(move)
    return moves


def _starts_with(game_moves: list[str], prefix: list[str]) -> bool:
    if len(game_moves) < len(prefix):
        return False
    return game_moves[: len(prefix)] == prefix


class TrapDatabase:
    def __init__(self, traps: list[TrapDefinition]) -> None:
        self._traps = traps

    def match_game(
        self, board: chess.Board, user_color: chess.Color
    ) -> list[TrapMatch]:
        game_moves = _game_san_sequence(board)
        matches: list[TrapMatch] = []

        for trap in self._traps:
            entered = any(
                _starts_with(game_moves, variant) for variant in trap.entry_san_variants
            )
            if not entered:
                continue

            sprung = any(
                _starts_with(game_moves, variant) for variant in trap.trap_san_variants
            )

            victim_is_white = trap.victim_side == "white"
            user_is_victim = (user_color == chess.WHITE and victim_is_white) or (
                user_color == chess.BLACK and not victim_is_white
            )

            if sprung:
                match_type = "sprung" if user_is_victim else "executed"
            else:
                match_type = "entered"

            matches.append(
                TrapMatch(
                    trap_id=trap.id,
                    match_type=match_type,
                    user_was_victim=user_is_victim,
                    mistake_ply=trap.mistake_ply if sprung else None,
                )
            )

        return matches

    def get_trap(self, trap_id: str) -> TrapDefinition | None:
        for trap in self._traps:
            if trap.id == trap_id:
                return trap
        return None

    @property
    def all_traps(self) -> list[TrapDefinition]:
        return list(self._traps)


def _load_trap_definitions(path: Path) -> list[TrapDefinition]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    traps = []
    for entry in data:
        entry_variants = [_parse_pgn_to_san(em) for em in entry["entry_moves"]]
        trap_variants = [_parse_pgn_to_san(tm) for tm in entry["trap_moves"]]

        traps.append(
            TrapDefinition(
                id=entry["id"],
                name=entry["name"],
                category=entry["category"],
                rating_range=tuple(entry["rating_range"]),
                victim_side=entry["victim_side"],
                entry_san_variants=entry_variants,
                trap_san_variants=trap_variants,
                mistake_ply=entry["mistake_ply"],
                mistake_san=entry["mistake_san"],
                refutation_pgn=entry["refutation_pgn"],
                refutation_move=entry["refutation_move"],
                refutation_note=entry["refutation_note"],
                recognition_tip=entry["recognition_tip"],
                tags=entry["tags"],
            )
        )
    return traps


@lru_cache(maxsize=1)
def get_trap_database(path: Path | None = None) -> TrapDatabase:
    if path is None:
        path = DEFAULT_FIXTURES_PATH / "traps.json"
    definitions = _load_trap_definitions(path)
    return TrapDatabase(definitions)

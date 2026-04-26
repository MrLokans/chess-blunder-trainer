from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess
import chess.polyglot

from blunder_tutor.constants import DEFAULT_FIXTURES_PATH


@dataclass(frozen=True)
class TrapPosition:
    pgn: str
    entry_hash: int
    mistake_san: str | None
    trigger_hash: int | None


@dataclass(frozen=True)
class TrapDefinition:
    id: str
    name: str
    category: str
    rating_range: tuple[int, int]
    victim_side: str
    positions: list[TrapPosition]
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


def _replay_pgn(pgn_str: str) -> chess.Board:
    board = chess.Board()
    for san in _parse_pgn_to_san(pgn_str):
        board.push_san(san)
    return board


class TrapDatabase:
    def __init__(self, traps: list[TrapDefinition]) -> None:
        self._traps = traps
        self._by_id: dict[str, TrapDefinition] = {t.id: t for t in traps}
        self._entry_lookup: dict[int, list[TrapDefinition]] = defaultdict(list)
        self._trigger_lookup: dict[int, list[tuple[TrapDefinition, TrapPosition]]] = (
            defaultdict(list)
        )

        for trap in traps:
            for pos in trap.positions:
                self._entry_lookup[pos.entry_hash].append(trap)
                if pos.mistake_san is not None:
                    self._trigger_lookup[pos.entry_hash].append((trap, pos))

    def match_game(
        self, board: chess.Board, user_color: chess.Color
    ) -> list[TrapMatch]:
        temp = board.root()
        entered: dict[str, int] = {}
        triggered: dict[str, int] = {}

        for ply, move in enumerate(board.move_stack):
            h = chess.polyglot.zobrist_hash(temp)

            triggers = self._trigger_lookup.get(h)
            if triggers:
                san = temp.san(move)
                for trap, pos in triggers:
                    if san == pos.mistake_san and trap.id not in triggered:
                        triggered[trap.id] = ply + 1

            entries = self._entry_lookup.get(h)
            if entries:
                for trap in entries:
                    if trap.id not in entered:
                        entered[trap.id] = ply

            temp.push(move)

        final_entries = self._entry_lookup.get(chess.polyglot.zobrist_hash(temp))
        if final_entries:
            for trap in final_entries:
                if trap.id not in entered:
                    entered[trap.id] = len(board.move_stack)

        results: list[TrapMatch] = []
        for trap_id in entered.keys() | triggered.keys():
            trap_def = self._by_id[trap_id]
            victim_is_white = trap_def.victim_side == "white"
            user_is_victim = (  # noqa: WPS408 — complementary, not duplicate: white-on-white-victim OR black-on-black-victim.
                user_color == chess.WHITE and victim_is_white
            ) or (user_color == chess.BLACK and not victim_is_white)

            triggered_ply = triggered.get(trap_id)
            if triggered_ply is not None:
                match_type = "sprung" if user_is_victim else "executed"
                mistake_ply = triggered_ply
            else:
                match_type = "entered"
                mistake_ply = None

            results.append(
                TrapMatch(
                    trap_id=trap_id,
                    match_type=match_type,
                    user_was_victim=user_is_victim,
                    mistake_ply=mistake_ply,
                )
            )

        return results

    def get_trap(self, trap_id: str) -> TrapDefinition | None:
        return self._by_id.get(trap_id)

    @property
    def all_traps(self) -> list[TrapDefinition]:
        return list(self._traps)


def _build_position_from_pgn_and_san(
    pgn: str, mistake_san: str | None = None
) -> TrapPosition:
    board = _replay_pgn(pgn)
    entry_hash = chess.polyglot.zobrist_hash(board)
    trigger_hash = None
    if mistake_san:
        board.push_san(mistake_san)
        trigger_hash = chess.polyglot.zobrist_hash(board)
    return TrapPosition(
        pgn=pgn,
        entry_hash=entry_hash,
        mistake_san=mistake_san,
        trigger_hash=trigger_hash,
    )


def _build_position_from_entry(entry: dict) -> TrapPosition:
    return _build_position_from_pgn_and_san(entry["pgn"], entry.get("mistake_san"))


def _load_trap_definitions(path: Path) -> list[TrapDefinition]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    traps = []
    for entry in data:
        positions = [_build_position_from_entry(p) for p in entry["positions"]]
        traps.append(
            TrapDefinition(
                id=entry["id"],
                name=entry["name"],
                category=entry["category"],
                rating_range=tuple(entry["rating_range"]),
                victim_side=entry["victim_side"],
                positions=positions,
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

"""What the tactics detector and the explanation generator say about a blunder, as plain
data, so case files and DB snapshots can pin it down."""

from __future__ import annotations

import io
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import chess
import chess.pgn

from blunder_tutor.analysis.tactics import classify_blunder_tactics
from blunder_tutor.utils.chess_utils import board_from_fen
from blunder_tutor.utils.explanation import I18nMessage, generate_explanation

DEMO_DB = Path(__file__).resolve().parents[2] / "demo" / "demo.sqlite3"


def _message(message: I18nMessage | None) -> dict[str, Any] | None:
    if message is None:
        return None
    return {"key": message.key, "params": message.params}


def describe_blunder(
    fen: str,
    blunder_uci: str,
    best_uci: str | None,
    cp_loss: int,
    best_line: list[str] | None = None,
) -> dict[str, Any]:
    board = board_from_fen(fen)
    best_move = chess.Move.from_uci(best_uci) if best_uci else None
    tactics = classify_blunder_tactics(
        board, chess.Move.from_uci(blunder_uci), best_move
    )
    explanation = generate_explanation(
        fen=fen,
        blunder_uci=blunder_uci,
        best_move_uci=best_uci,
        cp_loss=cp_loss,
        best_line=best_line,
    )
    return {
        "pattern": tactics.primary_pattern_name,
        "reason": tactics.blunder_reason,
        "blunder": _message(explanation.blunder),
        "best": _message(explanation.best_move),
    }


_BLUNDERS_SQL = """
    SELECT am.game_id, am.ply, am.san, am.uci, am.best_move_san, am.best_move_uci,
           am.best_line, am.cp_loss, g.pgn_content
    FROM analysis_moves am
    JOIN game_index_cache g ON g.game_id = am.game_id
    WHERE am.classification = 3
    ORDER BY am.game_id, am.ply
"""


def _boards_before_each_ply(pgn: str) -> dict[int, chess.Board]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    boards: dict[int, chess.Board] = {}
    for ply, move in enumerate(game.mainline_moves(), start=1):
        boards[ply] = board.copy(stack=False)
        board.push(move)
    return boards


def iter_db_blunders(db_path: Path) -> Iterator[dict[str, Any]]:
    # immutable: opening the WAL-mode demo DB read-only would still create -shm/-wal.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    boards: dict[int, chess.Board] = {}
    current_game = None
    try:
        for row in conn.execute(_BLUNDERS_SQL):
            if row["game_id"] != current_game:
                current_game = row["game_id"]
                boards = _boards_before_each_ply(row["pgn_content"])
            board = boards[row["ply"]]
            yield {
                "id": f"{row['game_id'][:12]}:{row['ply']}",
                "move": row["san"],
                "best_move": row["best_move_san"],
                **describe_blunder(
                    board.fen(),
                    row["uci"],
                    row["best_move_uci"],
                    row["cp_loss"],
                    row["best_line"].split() if row["best_line"] else None,
                ),
            }
    finally:
        conn.close()


def _format_message(message: dict[str, Any] | None) -> str:
    if message is None:
        return "-"
    key = (
        message["key"]
        .removeprefix("explanation.blunder.")
        .removeprefix("explanation.best.")
    )
    params = " ".join(
        f"{name}={str(value).removeprefix('chess.piece.')}"
        for name, value in sorted(message["params"].items())
    )
    return f"{key} {params}".rstrip()


def format_record(record: dict[str, Any]) -> str:
    return " | ".join(
        (
            f"{record['id']} {record['move']} (best {record['best_move']})",
            f"{record['pattern']}: {record['reason']}",
            f"blunder: {_format_message(record['blunder'])}",
            f"best: {_format_message(record['best'])}",
        )
    )

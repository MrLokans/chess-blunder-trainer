"""Beginner-friendly explanation generator for blunder puzzles.

Generates natural-language explanations of why a move was a blunder
and what the correct move achieves, using template-based logic.

Two-phase design:
  1. `generate_explanation()` analyzes the position and returns i18n keys + params
  2. `resolve_explanation()` formats them via TranslationManager for the active locale
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import chess

PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

# i18n key → piece type mapping
PIECE_I18N_KEYS = {
    chess.PAWN: "chess.piece.pawn",
    chess.KNIGHT: "chess.piece.knight",
    chess.BISHOP: "chess.piece.bishop",
    chess.ROOK: "chess.piece.rook",
    chess.QUEEN: "chess.piece.queen",
    chess.KING: "chess.piece.king",
}


@dataclass(frozen=True)
class I18nMessage:
    key: str
    params: dict[str, str | float] = field(default_factory=dict)


@dataclass(frozen=True)
class BlunderExplanation:
    blunder: I18nMessage | None
    best_move: I18nMessage | None


@dataclass(frozen=True)
class ResolvedExplanation:
    blunder_text: str
    best_move_text: str


def resolve_explanation(
    explanation: BlunderExplanation,
    t: Callable[..., str],
) -> ResolvedExplanation:
    blunder_text = ""
    if explanation.blunder:
        params = dict(explanation.blunder.params)
        # Resolve any piece key references (values starting with "chess.piece.")
        for k, v in list(params.items()):
            if isinstance(v, str) and v.startswith("chess.piece."):
                params[k] = t(v)
        blunder_text = t(explanation.blunder.key, **params)

    best_text = ""
    if explanation.best_move:
        params = dict(explanation.best_move.params)
        for k, v in list(params.items()):
            if isinstance(v, str) and v.startswith("chess.piece."):
                params[k] = t(v)
        best_text = t(explanation.best_move.key, **params)

    return ResolvedExplanation(blunder_text=blunder_text, best_move_text=best_text)


# ---------------------------------------------------------------------------
# Position analysis helpers
# ---------------------------------------------------------------------------


def _piece_key(board: chess.Board, square: chess.Square, case: str = "") -> str | None:
    piece = board.piece_at(square)
    if piece is None:
        return None
    base = PIECE_I18N_KEYS.get(piece.piece_type)
    if base is None:
        return None
    return f"{base}.{case}" if case else base


def _type_key(piece_type: chess.PieceType, case: str = "") -> str:
    base = PIECE_I18N_KEYS.get(piece_type, "")
    return f"{base}.{case}" if case else base


def _is_hanging(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    piece = board.piece_at(square)
    if piece is None or piece.color != color:
        return False
    enemy = not color
    return bool(board.is_attacked_by(enemy, square)) and not bool(
        board.attackers(color, square)
    )


def _move_gives_check(board: chess.Board, move: chess.Move) -> bool:
    b = board.copy()
    b.push(move)
    return b.is_check()


def _move_gives_mate(board: chess.Board, move: chess.Move) -> bool:
    b = board.copy()
    b.push(move)
    return b.is_checkmate()


def _has_pattern(tactical_pattern: str | None) -> bool:
    return bool(tactical_pattern) and tactical_pattern.lower() != "none"


def _find_new_attacks(
    board_before: chess.Board,
    board_after: chess.Board,
    attacker_color: chess.Color,
) -> list[tuple[chess.Square, chess.PieceType, int]]:
    enemy = not attacker_color
    results = []
    for sq in chess.SQUARES:
        piece = board_after.piece_at(sq)
        if piece and piece.color == enemy and piece.piece_type != chess.KING:
            was_attacked = board_before.is_attacked_by(attacker_color, sq)
            now_attacked = board_after.is_attacked_by(attacker_color, sq)
            if now_attacked and not was_attacked:
                val = PIECE_VALUES.get(piece.piece_type, 0)
                results.append((sq, piece.piece_type, val))
    return results


# ---------------------------------------------------------------------------
# Threat detection (null-move analysis)
# ---------------------------------------------------------------------------

_THREAT_MATE = "threatens_mate"
_THREAT_CAPTURE_CHECK = "threatens_capture_check"
_THREAT_PIECE = "creates_threat"
_THREAT_ATTACKS = "attacks_piece"


@dataclass(frozen=True)
class _Threat:
    kind: str
    piece_key: str = ""


def _detect_next_move_threat(board: chess.Board, move: chess.Move) -> _Threat | None:
    board_after = board.copy()
    board_after.push(move)
    player = board.turn

    new_attacks = _find_new_attacks(board, board_after, player)
    if new_attacks:
        new_attacks.sort(key=lambda x: x[2], reverse=True)
        best_target = new_attacks[0]
        if best_target[2] >= 5:
            # attacks_piece → accusative
            return _Threat(
                kind=_THREAT_ATTACKS,
                piece_key=_type_key(best_target[1], "acc"),
            )

    if board_after.is_check():
        return None
    null_board = board_after.copy()
    null_board.push(chess.Move.null())

    for candidate_move in null_board.legal_moves:
        piece = null_board.piece_at(candidate_move.from_square)
        if not piece or piece.color != player:
            continue
        board_check = null_board.copy()
        board_check.push(candidate_move)
        if board_check.is_checkmate():
            return _Threat(kind=_THREAT_MATE)
        if board_check.is_check():
            if null_board.is_capture(candidate_move):
                captured = null_board.piece_at(candidate_move.to_square)
                if captured and PIECE_VALUES.get(captured.piece_type, 0) >= 3:
                    # threatens_capture_check → genitive
                    return _Threat(
                        kind=_THREAT_CAPTURE_CHECK,
                        piece_key=_type_key(captured.piece_type, "gen"),
                    )
            if piece.piece_type != chess.PAWN:
                # creates_threat → genitive
                return _Threat(
                    kind=_THREAT_PIECE,
                    piece_key=_type_key(piece.piece_type, "gen"),
                )

    return None


def _count_material(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            total += PIECE_VALUES.get(piece.piece_type, 0)
    return total


# ---------------------------------------------------------------------------
# Blunder-side explanation
# ---------------------------------------------------------------------------


def _explain_blunder(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    cp_loss: int,
) -> I18nMessage | None:
    board_after = board.copy()
    board_after.push(blunder_move)

    moved_key_nom = _piece_key(board, blunder_move.from_square)
    if not moved_key_nom:
        return None
    moved_key_inst = _piece_key(board, blunder_move.from_square, "inst")

    # Piece moved to undefended square — nominative ("Your {piece} on ...")
    if _is_hanging(board_after, blunder_move.to_square, player_color):
        return I18nMessage(
            key="explanation.blunder.hanging_piece",
            params={
                "piece": moved_key_nom,
                "square": chess.square_name(blunder_move.to_square),
            },
        )

    # Moving away exposed another piece — instrumental + accusative
    for sq in chess.SQUARES:
        piece = board_after.piece_at(sq)
        if (
            piece
            and piece.color == player_color
            and sq != blunder_move.to_square
            and _is_hanging(board_after, sq, player_color)
            and not _is_hanging(board, sq, player_color)
        ):
            return I18nMessage(
                key="explanation.blunder.exposed_piece",
                params={
                    "piece": moved_key_inst,
                    "exposed": _type_key(piece.piece_type, "acc"),
                    "square": chess.square_name(sq),
                },
            )

    # Bad capture — instrumental ("Capturing with your {piece} ...")
    if board.is_capture(blunder_move):
        captured_piece = board.piece_at(blunder_move.to_square)
        mover = board.piece_at(blunder_move.from_square)
        if captured_piece and mover:
            captured_val = PIECE_VALUES.get(captured_piece.piece_type, 0)
            moved_val = PIECE_VALUES.get(mover.piece_type, 0)
            if moved_val > captured_val and board_after.is_attacked_by(
                not player_color, blunder_move.to_square
            ):
                return I18nMessage(
                    key="explanation.blunder.bad_capture",
                    params={"piece": moved_key_inst},
                )

    # Fallback: cp loss
    pawn_loss = cp_loss / 100
    if pawn_loss >= 1:
        return I18nMessage(
            key="explanation.blunder.cp_loss",
            params={"loss": f"{pawn_loss:.1f}"},
        )

    return None


# ---------------------------------------------------------------------------
# Best-move explanation
# ---------------------------------------------------------------------------

# Pattern key → i18n explanation key
_PATTERN_KEYS = {
    "fork": "explanation.best.pattern_fork",
    "pin": "explanation.best.pattern_pin",
    "skewer": "explanation.best.pattern_skewer",
    "back rank threat": "explanation.best.pattern_back_rank",
    "hanging piece": "explanation.best.pattern_hanging",
}


def _explain_best(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
    best_line: list[str] | None = None,
) -> I18nMessage | None:
    san = board.san(best_move)

    # Checkmate
    if _move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})

    # Check + capture — accusative ("captures the {piece}")
    if _move_gives_check(board, best_move):
        if board.is_capture(best_move):
            captured = board.piece_at(best_move.to_square)
            if captured:
                return I18nMessage(
                    key="explanation.best.capture_with_check",
                    params={
                        "san": san,
                        "piece": _type_key(captured.piece_type, "acc"),
                    },
                )
        if _has_pattern(tactical_pattern):
            return I18nMessage(
                key="explanation.best.check_with_pattern",
                params={"san": san, "pattern": tactical_pattern.lower()},
            )
        return I18nMessage(key="explanation.best.check_winning", params={"san": san})

    # Named tactical pattern
    if _has_pattern(tactical_pattern):
        pattern_lower = tactical_pattern.lower()
        # Discovered attack variants
        if "discovered" in pattern_lower:
            return I18nMessage(
                key="explanation.best.pattern_discovered", params={"san": san}
            )
        pattern_key = _PATTERN_KEYS.get(pattern_lower)
        if pattern_key:
            return I18nMessage(key=pattern_key, params={"san": san})
        # Generic pattern
        return I18nMessage(
            key="explanation.best.pattern_generic",
            params={"san": san, "pattern": pattern_lower},
        )

    # Simple winning capture — accusative ("wins the {piece}")
    if board.is_capture(best_move):
        captured = board.piece_at(best_move.to_square)
        if captured:
            return I18nMessage(
                key="explanation.best.wins_piece",
                params={
                    "san": san,
                    "piece": _type_key(captured.piece_type, "acc"),
                },
            )

    # Threat detection (null-move)
    threat = _detect_next_move_threat(board, best_move)
    if threat:
        threat_keys = {
            _THREAT_MATE: "explanation.best.threatens_mate",
            _THREAT_CAPTURE_CHECK: "explanation.best.threatens_capture_check",
            _THREAT_PIECE: "explanation.best.creates_threat",
            _THREAT_ATTACKS: "explanation.best.attacks_piece",
        }
        return I18nMessage(
            key=threat_keys[threat.kind],
            params={"san": san, "piece": threat.piece_key},
        )

    # Best-line material analysis
    if best_line and len(best_line) >= 3:
        line_board = board.copy()
        line_board.push(best_move)
        material_before = _count_material(board, board.turn)
        try:
            for move_san in best_line[1:]:
                line_board.push(line_board.parse_san(move_san))
            material_after = _count_material(line_board, board.turn)
            if material_after - material_before >= 3:
                return I18nMessage(
                    key="explanation.best.combination", params={"san": san}
                )
        except (ValueError, chess.IllegalMoveError):
            pass

    # cp-loss avoidance
    pawn_loss = cp_loss / 100
    if pawn_loss >= 1.5:
        return I18nMessage(
            key="explanation.best.avoids_loss",
            params={"san": san, "loss": f"{pawn_loss:.1f}"},
        )

    # Bare fallback
    return I18nMessage(key="explanation.best.fallback", params={"san": san})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_explanation(
    fen: str,
    blunder_uci: str,
    best_move_uci: str | None,
    tactical_pattern: str | None = None,
    cp_loss: int = 0,
    eval_before: int = 0,
    eval_after: int = 0,
    best_line: list[str] | None = None,
) -> BlunderExplanation:
    board = chess.Board(fen)
    player_color = board.turn

    try:
        blunder_move = chess.Move.from_uci(blunder_uci)
    except ValueError:
        return BlunderExplanation(blunder=None, best_move=None)

    if blunder_move not in board.legal_moves:
        return BlunderExplanation(blunder=None, best_move=None)

    blunder_msg = _explain_blunder(board, blunder_move, player_color, cp_loss)

    best_msg = None
    if best_move_uci:
        try:
            best_move = chess.Move.from_uci(best_move_uci)
            if best_move in board.legal_moves:
                best_msg = _explain_best(
                    board, best_move, tactical_pattern, cp_loss, best_line
                )
        except ValueError:
            pass

    return BlunderExplanation(blunder=blunder_msg, best_move=best_msg)

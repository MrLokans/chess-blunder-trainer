from __future__ import annotations

from collections.abc import Callable
from functools import partial

import chess

from blunder_tutor.analysis.explanation.blunder import explain_blunder
from blunder_tutor.analysis.explanation.board import (
    CENTIPAWNS_PER_PAWN,
    find_hanging_piece,
    is_hanging,
    is_retreat_to_safety,
    move_gives_check,
    move_gives_mate,
    piece_value,
)
from blunder_tutor.analysis.explanation.lines import PVAnalysis, analyze_pv, format_line
from blunder_tutor.analysis.explanation.messages import (
    BlunderExplanation,
    I18nMessage,
    type_key,
)
from blunder_tutor.analysis.explanation.structure import explain_best_structure
from blunder_tutor.analysis.explanation.threats import (
    THREAT_ATTACKS,
    THREAT_CAPTURE_CHECK,
    THREAT_MATE,
    THREAT_PIECE,
    detect_next_move_threat,
)
from blunder_tutor.analysis.tactics import PATTERN_LABELS, analyze_move_tactics
from blunder_tutor.utils.chess_utils import board_from_fen

# 1.5 pawns: clearly visible to a beginner without firing only on blowouts.
SIGNIFICANT_PAWN_LOSS = 1.5


def _has_pattern(tactical_pattern: str | None) -> bool:
    return bool(tactical_pattern) and tactical_pattern.lower() != "none"


def _explain_pv_mate(san: str, pv: PVAnalysis) -> I18nMessage:
    mate_depth = len(pv.moves_san) // 2 + 1
    if mate_depth <= 1:
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})
    return I18nMessage(
        key="explanation.best.pv_mate",
        params={
            "san": san,
            "moves": str(mate_depth),
            "line": format_line(pv.moves_san),
        },
    )


def _explain_pv_sacrifice(
    san: str, pv: PVAnalysis, tactical_pattern: str | None
) -> I18nMessage:
    assert pv.net_piece_won is not None
    piece_key = type_key(pv.net_piece_won, "acc")
    line_str = format_line(pv.moves_san)
    if _has_pattern(tactical_pattern):
        return I18nMessage(
            key="explanation.best.pv_wins_piece_via_pattern",
            params={
                "san": san,
                "piece": piece_key,
                "pattern": tactical_pattern.lower(),
                "line": line_str,
            },
        )
    return I18nMessage(
        key="explanation.best.pv_wins_piece_via_combination",
        params={"san": san, "piece": piece_key, "line": line_str},
    )


def _is_simple_first_capture(
    board: chess.Board, best_move: chess.Move, pv: PVAnalysis
) -> bool:
    if not board.is_capture(best_move):
        return False
    if len(pv.player_captures) != 1 or pv.net_piece_won is None:
        return False
    return pv.balance_gain >= piece_value(pv.net_piece_won)


def _explain_pv_material_win(
    board: chess.Board,
    best_move: chess.Move,
    san: str,
    pv: PVAnalysis,
) -> I18nMessage | None:
    if _is_simple_first_capture(board, best_move, pv):
        return None
    assert pv.net_piece_won is not None
    return I18nMessage(
        key="explanation.best.pv_wins_piece",
        params={
            "san": san,
            "piece": type_key(pv.net_piece_won, "acc"),
            "line": format_line(pv.moves_san),
        },
    )


def _explain_best_from_pv(
    board: chess.Board,
    best_move: chess.Move,
    pv: PVAnalysis,
    tactical_pattern: str | None,
) -> I18nMessage | None:
    san = board.san(best_move)
    if pv.gives_mate:
        return _explain_pv_mate(san, pv)
    if pv.is_sacrifice_combination and pv.net_piece_won:
        return _explain_pv_sacrifice(san, pv, tactical_pattern)
    if pv.balance_gain >= 1 and pv.net_piece_won:
        return _explain_pv_material_win(board, best_move, san, pv)
    if pv.balance_gain >= 3:
        return I18nMessage(key="explanation.best.combination", params={"san": san})
    return None


_PATTERN_KEYS = frozendict(
    {
        "fork": "explanation.best.pattern_fork",
        "skewer": "explanation.best.pattern_skewer",
        "back rank threat": "explanation.best.pattern_back_rank",
    }
)


_THREAT_KEYS = frozendict(
    {
        THREAT_MATE: "explanation.best.threatens_mate",
        THREAT_CAPTURE_CHECK: "explanation.best.threatens_capture_check",
        THREAT_PIECE: "explanation.best.creates_threat",
        THREAT_ATTACKS: "explanation.best.attacks_piece",
    }
)


def _explain_best_check(
    board: chess.Board,
    best_move: chess.Move,
    san: str,
    tactical_pattern: str | None,
) -> I18nMessage | None:
    if board.is_capture(best_move):
        captured = board.piece_at(best_move.to_square)
        if captured:
            return I18nMessage(
                key="explanation.best.capture_with_check",
                params={"san": san, "piece": type_key(captured.piece_type, "acc")},
            )
    if _has_pattern(tactical_pattern):
        return I18nMessage(
            key="explanation.best.check_with_pattern",
            params={"san": san, "pattern": tactical_pattern.lower()},
        )
    hanging = find_hanging_piece(board, best_move, board.turn)
    if hanging is not None:
        piece_type, sq = hanging
        return I18nMessage(
            key="explanation.best.check_wins_hanging",
            params={
                "san": san,
                "piece": type_key(piece_type, "acc"),
                "square": chess.square_name(sq),
            },
        )
    return None


def _is_capturable_hanging(
    board: chess.Board, best_move: chess.Move, captured: chess.Piece | None
) -> bool:
    if captured is None or not board.is_capture(best_move):
        return False
    return is_hanging(board, best_move.to_square, not board.turn)


def _explain_best_hanging_capture(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    captured = board.piece_at(best_move.to_square)
    if captured is None or not _is_capturable_hanging(board, best_move, captured):
        return None
    return I18nMessage(
        key="explanation.best.pattern_hanging_piece",
        params={
            "san": san,
            "piece": type_key(captured.piece_type, "acc"),
            "square": chess.square_name(best_move.to_square),
        },
    )


def _explain_best_pattern(san: str, tactical_pattern: str) -> I18nMessage:
    pattern_lower = tactical_pattern.lower()
    if "discovered" in pattern_lower:
        return I18nMessage(
            key="explanation.best.pattern_discovered", params={"san": san}
        )
    pattern_key = _PATTERN_KEYS.get(pattern_lower)
    if pattern_key:
        return I18nMessage(key=pattern_key, params={"san": san})
    return I18nMessage(
        key="explanation.best.pattern_generic",
        params={"san": san, "pattern": pattern_lower},
    )


def _explain_best_capture(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    if not board.is_capture(best_move):
        return None
    captured = board.piece_at(best_move.to_square)
    capturer = board.piece_at(best_move.from_square)
    if captured is None or capturer is None:
        return None
    key = _capture_outcome_key(board, best_move, captured, capturer)
    if key is None:
        return None
    return I18nMessage(
        key=key, params={"san": san, "piece": type_key(captured.piece_type, "acc")}
    )


def _capture_outcome_key(
    board: chess.Board,
    capture: chess.Move,
    captured: chess.Piece,
    capturer: chess.Piece,
) -> str | None:
    captured_value = piece_value(captured.piece_type)
    capturer_value = piece_value(capturer.piece_type)
    board_after = board.copy()
    board_after.push(capture)
    recapturable = board_after.is_attacked_by(board_after.turn, capture.to_square)
    if captured_value > capturer_value or not recapturable:
        return "explanation.best.wins_piece"
    if captured_value == capturer_value:
        return "explanation.best.trades_piece"
    # A defended lower-value target: the static view can't tell why it works.
    return None


def _explain_best_threat(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    threat = detect_next_move_threat(board, best_move)
    if threat is None:
        return None
    return I18nMessage(
        key=_THREAT_KEYS[threat.kind],
        params={"san": san, "piece": threat.piece_key},
    )


def _explain_best_retreat(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    retreat = is_retreat_to_safety(board, best_move)
    if retreat is None:
        return None
    piece_type, _from_sq = retreat
    return I18nMessage(
        key="explanation.best.saves_piece",
        params={"san": san, "piece": type_key(piece_type, "acc")},
    )


def _explain_best_loss_avoidance(san: str, cp_loss: int) -> I18nMessage:
    pawn_loss = cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss >= SIGNIFICANT_PAWN_LOSS:
        return I18nMessage(
            key="explanation.best.avoids_loss",
            params={"san": san, "loss": f"{pawn_loss:.1f}"},
        )
    return I18nMessage(key="explanation.best.fallback", params={"san": san})


def _try_static_strategies(
    board: chess.Board,
    best_move: chess.Move,
    san: str,
    tactical_pattern: str | None,
    structure: I18nMessage | None,
) -> I18nMessage | None:
    if _has_pattern(tactical_pattern):
        return _explain_best_pattern(san, tactical_pattern)
    # Lazy: the threat search is the expensive one and runs only if nothing earlier fits.
    strategies: tuple[Callable[[], I18nMessage | None], ...] = (
        partial(_explain_best_hanging_capture, board, best_move, san),
        lambda: structure,
        partial(_explain_best_retreat, board, best_move, san),
        partial(_explain_best_capture, board, best_move, san),
        partial(_explain_best_threat, board, best_move, san),
    )
    return next(
        (message for strategy in strategies if (message := strategy()) is not None),
        None,
    )


def _explain_best_static(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
    structure: I18nMessage | None = None,
) -> I18nMessage | None:
    san = board.san(best_move)
    if move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})
    if move_gives_check(board, best_move):
        check_msg = _explain_best_check(board, best_move, san, tactical_pattern)
        if check_msg is not None:
            return check_msg
    static_msg = _try_static_strategies(
        board, best_move, san, tactical_pattern, structure
    )
    if static_msg is not None:
        return static_msg
    return _explain_best_loss_avoidance(san, cp_loss)


def _explain_best(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
    best_line: list[str] | None = None,
    structure: I18nMessage | None = None,
) -> I18nMessage | None:
    if move_gives_mate(board, best_move):
        return I18nMessage(
            key="explanation.best.checkmate", params={"san": board.san(best_move)}
        )

    if best_line and len(best_line) >= 2:
        pv = analyze_pv(board, best_move, best_line)
        if pv:
            pv_msg = _explain_best_from_pv(board, best_move, pv, tactical_pattern)
            if pv_msg:
                return pv_msg

    return _explain_best_static(board, best_move, tactical_pattern, cp_loss, structure)


def _parse_legal_move(board: chess.Board, uci: str | None) -> chess.Move | None:
    if not uci:
        return None
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return None
    if move not in board.legal_moves:
        return None
    return move


def _best_move_pattern(board: chess.Board, best_move: chess.Move) -> str | None:
    tactic = analyze_move_tactics(board, best_move)
    return PATTERN_LABELS[tactic.pattern] if tactic else None


def generate_explanation(
    fen: str,
    blunder_uci: str,
    best_move_uci: str | None,
    cp_loss: int = 0,
    best_line: list[str] | None = None,
    refutation_line: list[str] | None = None,
) -> BlunderExplanation:
    board = board_from_fen(fen)
    blunder_move = _parse_legal_move(board, blunder_uci)
    if blunder_move is None:
        return BlunderExplanation(blunder=None, best_move=None)

    best_move = _parse_legal_move(board, best_move_uci)
    blunder_msg = explain_blunder(
        board, blunder_move, board.turn, cp_loss, best_move, refutation_line
    )
    best_msg = (
        _explain_best(
            board,
            best_move,
            _best_move_pattern(board, best_move),
            cp_loss,
            best_line,
            explain_best_structure(board, blunder_move, best_line, refutation_line),
        )
        if best_move
        else None
    )
    return BlunderExplanation(blunder=blunder_msg, best_move=best_msg)

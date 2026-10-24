from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

import chess

from blunder_tutor.analysis.explanation.board import (
    CENTIPAWNS_PER_PAWN,
    find_hanging_piece,
    has_legal_capture,
    is_hanging,
    is_retreat_to_safety,
    move_gives_check,
    move_gives_mate,
    piece_value,
)
from blunder_tutor.analysis.explanation.lines import PVAnalysis, analyze_pv, format_line
from blunder_tutor.analysis.explanation.messages import I18nMessage, type_key
from blunder_tutor.analysis.explanation.puzzle import Puzzle
from blunder_tutor.analysis.explanation.structure import explain_best_structure
from blunder_tutor.analysis.explanation.threats import (
    THREAT_ATTACKS,
    THREAT_CAPTURE_CHECK,
    THREAT_MATE,
    THREAT_PIECE,
    detect_next_move_threat,
)
from blunder_tutor.analysis.tactics import PATTERN_LABELS, analyze_move_tactics

# 1.5 pawns: clearly visible to a beginner without firing only on blowouts.
SIGNIFICANT_PAWN_LOSS = 1.5

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


@dataclass(frozen=True)
class _BestMove:
    puzzle: Puzzle
    move: chess.Move

    @property
    def board(self) -> chess.Board:
        return self.puzzle.board

    @cached_property
    def san(self) -> str:
        return self.board.san(self.move)

    @cached_property
    def pattern(self) -> str | None:
        """The best move's own tactic: a puzzle's stored pattern may describe what the
        blunder allowed instead."""
        tactic = analyze_move_tactics(self.board, self.move)
        label = PATTERN_LABELS[tactic.pattern].lower() if tactic else None
        return None if label == "none" else label

    @cached_property
    def line(self) -> PVAnalysis | None:
        best_line = self.puzzle.best_line
        if not best_line or len(best_line) < 2:
            return None
        line = analyze_pv(self.board, self.move, best_line)
        # Engine lines stop at mate, so an even length means the player got mated: a
        # line that ends that way explains nothing about why the move is best.
        if line is not None and line.gives_mate and len(line.moves_san) % 2 == 0:
            return None
        return line

    @cached_property
    def gives_check(self) -> bool:
        return move_gives_check(self.board, self.move)

    @cached_property
    def captured(self) -> chess.Piece | None:
        if not self.board.is_capture(self.move):
            return None
        return self.board.piece_at(self.move.to_square)

    def say(self, key: str, **params: str) -> I18nMessage:
        return I18nMessage(key=key, params={"san": self.san, **params})


def _mate_in_one(best: _BestMove) -> I18nMessage | None:
    if not move_gives_mate(best.board, best.move):
        return None
    return best.say("explanation.best.checkmate")


def _line_mate(best: _BestMove) -> I18nMessage | None:
    line = best.line
    if line is None or not line.gives_mate:
        return None
    return best.say(
        "explanation.best.pv_mate",
        moves=str(len(line.moves_san) // 2 + 1),
        line=format_line(line.moves_san),
    )


def _line_sacrifice(best: _BestMove) -> I18nMessage | None:
    line = best.line
    if line is None or not line.is_sacrifice_combination:
        return None
    if line.net_piece_won is None:
        return None
    piece = type_key(line.net_piece_won, "acc")
    if best.pattern:
        return best.say(
            "explanation.best.pv_wins_piece_via_pattern",
            piece=piece,
            pattern=best.pattern,
            line=format_line(line.moves_san),
        )
    return best.say(
        "explanation.best.pv_wins_piece_via_combination",
        piece=piece,
        line=format_line(line.moves_san),
    )


def _is_simple_first_capture(best: _BestMove, line: PVAnalysis) -> bool:
    if best.captured is None or line.net_piece_won is None:
        return False
    if len(line.player_captures) != 1:
        return False
    return line.balance_gain >= piece_value(line.net_piece_won)


def _line_material_win(best: _BestMove) -> I18nMessage | None:
    line = best.line
    if line is None or line.balance_gain < 1 or line.net_piece_won is None:
        return None
    piece = type_key(line.net_piece_won, "acc")
    if not _is_simple_first_capture(best, line):
        return best.say(
            "explanation.best.pv_wins_piece",
            piece=piece,
            line=format_line(line.moves_san),
        )
    # A check or a named tactic is the more instructive sentence, so leave those to
    # their steps; otherwise the line confirms the capture nets material, which the
    # static capture step can't see.
    if best.pattern or best.gives_check:
        return None
    return _hanging_capture(best) or best.say(
        "explanation.best.wins_piece", piece=piece
    )


def _line_combination(best: _BestMove) -> I18nMessage | None:
    line = best.line
    if line is None or line.net_piece_won is not None or line.balance_gain < 3:
        return None
    return best.say("explanation.best.combination")


def _check_capture(best: _BestMove) -> I18nMessage | None:
    if not best.gives_check or best.captured is None:
        return None
    return best.say(
        "explanation.best.capture_with_check",
        piece=type_key(best.captured.piece_type, "acc"),
    )


def _check_pattern(best: _BestMove) -> I18nMessage | None:
    if not best.gives_check or best.pattern is None:
        return None
    return best.say("explanation.best.check_with_pattern", pattern=best.pattern)


def _check_wins_hanging(best: _BestMove) -> I18nMessage | None:
    if not best.gives_check:
        return None
    hanging = find_hanging_piece(best.board, best.move, best.board.turn)
    if hanging is None:
        return None
    piece_type, sq = hanging
    return best.say(
        "explanation.best.check_wins_hanging",
        piece=type_key(piece_type, "acc"),
        square=chess.square_name(sq),
    )


def _pattern(best: _BestMove) -> I18nMessage | None:
    pattern = best.pattern
    if pattern is None:
        return None
    if "discovered" in pattern:
        return best.say("explanation.best.pattern_discovered")
    pattern_key = _PATTERN_KEYS.get(pattern)
    if pattern_key:
        return best.say(pattern_key)
    return best.say("explanation.best.pattern_generic", pattern=pattern)


def _hanging_capture(best: _BestMove) -> I18nMessage | None:
    captured = best.captured
    if captured is None or not is_hanging(
        best.board, best.move.to_square, not best.board.turn
    ):
        return None
    return best.say(
        "explanation.best.pattern_hanging_piece",
        piece=type_key(captured.piece_type, "acc"),
        square=chess.square_name(best.move.to_square),
    )


def _structure(best: _BestMove) -> I18nMessage | None:
    puzzle = best.puzzle
    return explain_best_structure(
        puzzle.board, puzzle.blunder_move, puzzle.best_line, puzzle.refutation_line
    )


def _retreat(best: _BestMove) -> I18nMessage | None:
    retreat = is_retreat_to_safety(best.board, best.move)
    if retreat is None:
        return None
    piece_type, _from_sq = retreat
    return best.say("explanation.best.saves_piece", piece=type_key(piece_type, "acc"))


def _capture_outcome_key(best: _BestMove, captured: chess.Piece) -> str | None:
    capturer = best.board.piece_at(best.move.from_square)
    if capturer is None:
        return None
    captured_value = piece_value(captured.piece_type)
    capturer_value = piece_value(capturer.piece_type)
    board_after = best.board.copy()
    board_after.push(best.move)
    recapturable = has_legal_capture(board_after, best.move.to_square)
    if captured_value > capturer_value or not recapturable:
        return "explanation.best.wins_piece"
    if captured_value == capturer_value:
        return "explanation.best.trades_piece"
    # A defended lower-value target: the static view can't tell why it works.
    return None


def _capture(best: _BestMove) -> I18nMessage | None:
    captured = best.captured
    if captured is None:
        return None
    key = _capture_outcome_key(best, captured)
    if key is None:
        return None
    return best.say(key, piece=type_key(captured.piece_type, "acc"))


def _threat(best: _BestMove) -> I18nMessage | None:
    threat = detect_next_move_threat(best.board, best.move)
    if threat is None:
        return None
    return best.say(_THREAT_KEYS[threat.kind], piece=threat.piece_key)


def _loss_avoidance(best: _BestMove) -> I18nMessage:
    pawn_loss = best.puzzle.cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss >= SIGNIFICANT_PAWN_LOSS:
        return best.say("explanation.best.avoids_loss", loss=f"{pawn_loss:.1f}")
    return best.say("explanation.best.fallback")


# First match wins. Steps that read the engine line come before the static ones, a
# check is worded before quiet reasons, and the threat search (the slowest) runs last.
_BEST_STRATEGIES: tuple[Callable[[_BestMove], I18nMessage | None], ...] = (
    _mate_in_one,
    _line_mate,
    _line_sacrifice,
    _line_material_win,
    _line_combination,
    _check_capture,
    _check_pattern,
    _check_wins_hanging,
    _pattern,
    _hanging_capture,
    _structure,
    _retreat,
    _capture,
    _threat,
    _loss_avoidance,
)


def explain_best(puzzle: Puzzle) -> I18nMessage | None:
    if puzzle.best_move is None:
        return None
    best = _BestMove(puzzle, puzzle.best_move)
    return next(
        (
            message
            for strategy in _BEST_STRATEGIES
            if (message := strategy(best)) is not None
        ),
        None,
    )

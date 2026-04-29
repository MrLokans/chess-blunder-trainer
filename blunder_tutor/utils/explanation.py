"""Beginner-friendly explanation generator for blunder puzzles.

Background
----------
Translating a chess engine's numerical evaluation into a human-readable
sentence is a known hard problem.  Engines output centipawn scores and
best-move sequences; they never explain *why*.  The explanation must be
reverse-engineered from the output — and the approaches in the literature
range from rigid rule-based templates to LLM-powered generation.

The academic lineage starts with Bratko / Guid / Sadikov (Ljubljana,
2006-2013), who compared positional features across consecutive positions
and filled sentence templates ("The move aims to centralize the Knight").
Jhamtani et al. (CMU, ACL 2018) scaled this up with neural seq2seq models
trained on 298K move-commentary pairs.  The current frontier — Kim et al.
(2024, concept-guided commentary) and Soliman & Ehab (2025, Caïssa AI) —
pairs engine analysis with LLMs grounded in structured chess concepts.

A recurring finding across all of this work: **LLMs hallucinate when asked
to evaluate positions, but perform well when asked to *explain* pre-computed
engine analysis.**  The engine provides ground truth; the language layer
translates it.  See docs/explaining-engines.md for the full survey.

Our approach
------------
We don't use an LLM.  Instead we adopt the most reliable offline strategy
from the literature: **walk the engine's principal variation (PV) and
describe what concretely happens** — who captures what, whether the line
ends in check or mate, what the net material change is.  The PV is the
single most trustworthy artefact Stockfish produces: it shows the actual
sequence of best play for both sides.

This "PV-first" design replaced an earlier template-only system that tried
to infer explanations from static pattern detection (forks, pins, hanging
pieces).  That approach repeatedly misattributed causality: a pre-existing
pin was blamed on the blunder, a defended queen was called "undefended",
a bishop sacrifice for a pawn was described as "captures the pawn with
check" when the real point was winning the queen three moves later.

Architecture (three phases)
---------------------------
``_explain_best`` resolves the best-move explanation in priority order:

1. **Immediate mate** — if the best move is checkmate, say so.  No PV
   needed; this is always unambiguous.

2. **PV analysis** (``_analyze_pv`` → ``_explain_best_from_pv``) — walk
   the engine's best line (up to 5 half-moves), track every capture by
   both sides, compute the material-balance delta, detect mate in the
   line.  From the structured ``PVAnalysis`` result:

   - *Mate in N*: "Qf7+ leads to checkmate in 3 moves: Qf7+ Kh8 Qf8#"
   - *Sacrifice combination*: the player gives up material (opponent
     captures something) but ends with a net gain ≥ 3 pawns.  If a
     tactical pattern label is available from ``analysis/tactics.py``,
     it enriches the message: "Bxh7+ wins the queen via discovered
     attack: Bxh7+ Kxh7 Ng5+ Kg8 Qxd5".  Otherwise: "wins the queen
     through a combination".
   - *Non-sacrifice material win*: net gain ≥ 1 pawn through a
     multi-move sequence that isn't a simple direct capture.
   - *Simple direct capture*: the PV deliberately returns ``None`` so
     the static layer can describe it more concisely ("wins the rook")
     without redundantly showing the one-move line.

3. **Static fallback** (``_explain_best_static``) — used when no PV is
   available or when the PV is uninformative (no material gain, no mate).
   This is the old template system, kept as a safety net:

   - Check + capture ("captures the rook with check")
   - Named tactical pattern ("creates a fork")
   - Simple capture ("wins the bishop")
   - Null-move threat detection ("threatens checkmate")
   - Centipawn-loss avoidance ("avoids losing 3.5 pawns of advantage")
   - Bare fallback ("the best move is Nf3")

Blunder-side explanation
------------------------
``_explain_blunder`` is simpler and still fully static: it examines the
position *after* the blunder was played and checks, in order:

- Did the player miss an immediate mate?
- Did the moved piece land on an undefended square?
- Did moving the piece expose another piece?
- Was it a bad capture (trading a high-value piece for a low-value one)?
- Fallback: report the centipawn loss as pawn equivalents.

i18n design
-----------
Explanations are produced as ``I18nMessage(key, params)`` — never as raw
text.  Piece names are passed as i18n key references (e.g.
``chess.piece.queen.acc`` for accusative case), enabling grammatically
correct translations in morphologically rich languages (Russian, Polish,
Ukrainian).  The ``resolve_explanation`` function pairs the message with
a ``t()`` translator to produce the final ``ResolvedExplanation``.

All explanation keys live under the ``explanation.blunder.*`` and
``explanation.best.*`` namespaces in ``locales/*.json``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType

import chess

CENTIPAWNS_PER_PAWN = 100

# Threshold for "this best move avoids a significant loss" copy — 1.5
# pawns is large enough that a beginner would clearly see the difference
# in evaluation, small enough that it doesn't only fire on tactical
# blowouts.
SIGNIFICANT_PAWN_LOSS = 1.5


PIECE_NAMES = MappingProxyType(
    {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king",
    }
)

PIECE_VALUES = MappingProxyType(
    {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }
)

# i18n key → piece type mapping
PIECE_I18N_KEYS = {
    chess.PAWN: "chess.piece.pawn",
    chess.KNIGHT: "chess.piece.knight",
    chess.BISHOP: "chess.piece.bishop",
    chess.ROOK: "chess.piece.rook",
    chess.QUEEN: "chess.piece.queen",
    chess.KING: "chess.piece.king",
}

_PIECE_KEY_PREFIX = "chess.piece."


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


def _resolve_message(message: I18nMessage | None, t: Callable[..., str]) -> str:
    if message is None:
        return ""
    params = dict(message.params)
    for key, value in list(params.items()):
        if isinstance(value, str) and value.startswith(_PIECE_KEY_PREFIX):
            params[key] = t(value)
    return t(message.key, **params)


def resolve_explanation(
    explanation: BlunderExplanation,
    t: Callable[..., str],
) -> ResolvedExplanation:
    return ResolvedExplanation(
        blunder_text=_resolve_message(explanation.blunder, t),
        best_move_text=_resolve_message(explanation.best_move, t),
    )


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


def _piece_value(piece_type: chess.PieceType) -> int:
    return PIECE_VALUES.get(piece_type, 0)


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
                results.append((sq, piece.piece_type, _piece_value(piece.piece_type)))
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


def _threat_from_new_attacks(
    board: chess.Board, board_after: chess.Board, player: chess.Color
) -> _Threat | None:
    new_attacks = _find_new_attacks(board, board_after, player)
    if not new_attacks:
        return None
    new_attacks.sort(key=lambda x: x[2], reverse=True)
    best_target = new_attacks[0]
    if best_target[2] < 5:
        return None
    return _Threat(kind=_THREAT_ATTACKS, piece_key=_type_key(best_target[1], "acc"))


def _classify_null_move_threat(
    null_board: chess.Board,
    candidate_move: chess.Move,
    piece: chess.Piece,
    player: chess.Color,
) -> _Threat | None:
    board_check = null_board.copy()
    board_check.push(candidate_move)
    if board_check.is_checkmate():
        return _Threat(kind=_THREAT_MATE)
    if not board_check.is_check():
        return None
    if null_board.is_capture(candidate_move):
        captured = null_board.piece_at(candidate_move.to_square)
        if captured and _piece_value(captured.piece_type) >= 3:
            return _Threat(
                kind=_THREAT_CAPTURE_CHECK,
                piece_key=_type_key(captured.piece_type, "gen"),
            )
    if piece.piece_type != chess.PAWN:
        return _Threat(
            kind=_THREAT_PIECE,
            piece_key=_type_key(piece.piece_type, "gen"),
        )
    return None


def _threat_from_null_move(
    board_after: chess.Board, player: chess.Color
) -> _Threat | None:
    if board_after.is_check():
        return None
    null_board = board_after.copy()
    null_board.push(chess.Move.null())

    for candidate_move in null_board.legal_moves:
        piece = null_board.piece_at(candidate_move.from_square)
        if not piece or piece.color != player:
            continue
        threat = _classify_null_move_threat(null_board, candidate_move, piece, player)
        if threat is not None:
            return threat
    return None


def _detect_next_move_threat(board: chess.Board, move: chess.Move) -> _Threat | None:
    board_after = board.copy()
    board_after.push(move)
    player = board.turn

    new_attack_threat = _threat_from_new_attacks(board, board_after, player)
    if new_attack_threat is not None:
        return new_attack_threat
    return _threat_from_null_move(board_after, player)


def _iter_hanging_enemies(board: chess.Board, enemy: chess.Color):
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if (
            piece
            and piece.color == enemy
            and piece.piece_type != chess.KING
            and _is_hanging(board, sq, enemy)
        ):
            yield sq, piece


def _find_hanging_piece(
    board: chess.Board,
    move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(move)
    enemy = not player_color
    candidates = [
        (_piece_value(piece.piece_type), piece.piece_type, sq)
        for sq, piece in _iter_hanging_enemies(board_after, enemy)
    ]
    if not candidates:
        return None
    _, piece_type, sq = max(candidates, key=lambda c: c[0])
    return (piece_type, sq)


def _min_attacker_value(
    board: chess.Board,
    sq: chess.Square,
    attacker_color: chess.Color,
) -> int | None:
    attackers = board.attackers(attacker_color, sq)
    if not attackers:
        return None
    return min(
        _piece_value(board.piece_at(a).piece_type)
        for a in attackers
        if board.piece_at(a)
    )


def _is_under_profitable_attack(
    board: chess.Board,
    sq: chess.Square,
    piece_val: int,
    enemy: chess.Color,
) -> bool:
    min_attacker = _min_attacker_value(board, sq, enemy)
    return min_attacker is not None and min_attacker < piece_val


def _is_ignored_threat(
    board: chess.Board,
    board_after: chess.Board,
    sq: chess.Square,
    piece: chess.Piece,
    blunder_move: chess.Move,
    player_color: chess.Color,
    enemy: chess.Color,
) -> bool:
    piece_val = _piece_value(piece.piece_type)
    if piece_val < 3 or blunder_move.from_square == sq:
        return False
    if not _is_under_profitable_attack(board, sq, piece_val, enemy):
        return False
    if board.is_capture(blunder_move) and blunder_move.to_square in board.attackers(
        enemy, sq
    ):
        return False
    piece_after = board_after.piece_at(sq)
    if piece_after is None or piece_after.color != player_color:
        return False
    return board_after.is_attacked_by(enemy, sq)


def _find_ignored_threat(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(blunder_move)
    enemy = not player_color
    candidates: list[tuple[int, chess.PieceType, chess.Square]] = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None or piece.color != player_color:
            continue
        if _is_ignored_threat(
            board, board_after, sq, piece, blunder_move, player_color, enemy
        ):
            candidates.append((_piece_value(piece.piece_type), piece.piece_type, sq))
    if not candidates:
        return None
    _, piece_type, found_sq = max(candidates, key=lambda c: c[0])
    return (piece_type, found_sq)


def _is_safe_destination(
    board_after: chess.Board,
    dest: chess.Square,
    enemy: chess.Color,
    piece_val: int,
) -> bool:
    for attacker_sq in board_after.attackers(enemy, dest):
        attacker = board_after.piece_at(attacker_sq)
        if attacker and _piece_value(attacker.piece_type) < piece_val:
            return False
    return True


def _retreat_candidate(
    board: chess.Board, best_move: chess.Move
) -> tuple[chess.Piece, int, chess.Color] | None:
    if board.is_capture(best_move):
        return None
    player = board.turn
    piece = board.piece_at(best_move.from_square)
    if piece is None or piece.color != player or piece.piece_type == chess.KING:
        return None
    piece_val = _piece_value(piece.piece_type)
    if piece_val < 3:
        return None
    enemy = not player
    if not _is_under_profitable_attack(board, best_move.from_square, piece_val, enemy):
        return None
    return (piece, piece_val, enemy)


def _is_retreat_to_safety(
    board: chess.Board,
    best_move: chess.Move,
) -> tuple[chess.PieceType, chess.Square] | None:
    candidate = _retreat_candidate(board, best_move)
    if candidate is None:
        return None
    piece, piece_val, enemy = candidate
    board_after = board.copy()
    board_after.push(best_move)
    if not _is_safe_destination(board_after, best_move.to_square, enemy, piece_val):
        return None
    return (piece.piece_type, best_move.from_square)


def _count_material(board: chess.Board, color: chess.Color) -> int:
    return sum(
        _piece_value(piece.piece_type)
        for sq in chess.SQUARES
        if (piece := board.piece_at(sq)) and piece.color == color
    )


def _material_balance(board: chess.Board, color: chess.Color) -> int:
    return _count_material(board, color) - _count_material(board, not color)


# ---------------------------------------------------------------------------
# PV (principal variation) analysis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PVCapture:
    piece_type: chess.PieceType
    by_color: chess.Color


@dataclass
class _PVWalkState:
    line_board: chess.Board
    player_caps: list[_PVCapture] = field(default_factory=list)
    opp_caps: list[_PVCapture] = field(default_factory=list)
    gives_mate: bool = False


@dataclass(frozen=True)
class PVAnalysis:
    """Structured result from walking the engine's principal variation."""

    moves_san: list[str]
    gives_check: bool
    gives_mate: bool
    balance_gain: int
    player_captures: list[_PVCapture]
    opponent_captures: list[_PVCapture]
    best_opponent_loss: chess.PieceType | None

    @property
    def is_sacrifice_combination(self) -> bool:
        return bool(self.opponent_captures) and self.balance_gain >= 3

    @property
    def net_piece_won(self) -> chess.PieceType | None:
        if self.balance_gain < 1:
            return None
        return self.best_opponent_loss


def _record_capture_if_any(
    state: _PVWalkState,
    prev_board: chess.Board,
    move: chess.Move,
    side: chess.Color,
    player: chess.Color,
) -> None:
    if not prev_board.is_capture(move):
        return
    captured = prev_board.piece_at(move.to_square)
    if captured is None:
        return
    cap = _PVCapture(captured.piece_type, side)
    if side == player:
        state.player_caps.append(cap)
    else:
        state.opp_caps.append(cap)


def _walk_pv_continuation(
    state: _PVWalkState,
    best_line: list[str],
    player: chess.Color,
) -> bool:
    """Returns True if the line walked cleanly, False on SAN parse failure."""
    for move_san in best_line[1:]:
        prev_board = state.line_board.copy()
        try:
            move = state.line_board.parse_san(move_san)
        except (ValueError, chess.IllegalMoveError):
            return False
        side = state.line_board.turn
        state.line_board.push(move)
        _record_capture_if_any(state, prev_board, move, side, player)
        if state.line_board.is_checkmate():
            state.gives_mate = True
            return True
    return True


def _best_opponent_loss(
    player_caps: list[_PVCapture],
) -> chess.PieceType | None:
    if not player_caps:
        return None
    return max((c.piece_type for c in player_caps), key=_piece_value)


def _analyze_pv(
    board: chess.Board,
    best_move: chess.Move,
    best_line: list[str],
) -> PVAnalysis | None:
    player = board.turn
    state = _PVWalkState(line_board=board.copy())
    balance_before = _material_balance(board, player)

    try:
        state.line_board.push(best_move)
    except (ValueError, chess.IllegalMoveError):
        return None

    gives_check = state.line_board.is_check()
    if state.line_board.is_checkmate():
        state.gives_mate = True
    if board.is_capture(best_move):
        captured = board.piece_at(best_move.to_square)
        if captured:
            state.player_caps.append(_PVCapture(captured.piece_type, player))

    walked_cleanly = state.gives_mate or _walk_pv_continuation(state, best_line, player)
    # Original parity: if SAN parse fails mid-line AND nothing useful was
    # captured AND the move doesn't even give check, the analysis is too
    # unreliable to act on — fall back to the static layer.
    if not walked_cleanly and not state.player_caps and not gives_check:
        return None

    return PVAnalysis(
        moves_san=best_line,
        gives_check=gives_check,
        gives_mate=state.gives_mate,
        balance_gain=_material_balance(state.line_board, player) - balance_before,
        player_captures=state.player_caps,
        opponent_captures=state.opp_caps,
        best_opponent_loss=_best_opponent_loss(state.player_caps),
    )


def _format_line(moves: list[str], max_moves: int = 5) -> str:
    return " ".join(moves[:max_moves])


def _explain_pv_mate(san: str, pv: PVAnalysis) -> I18nMessage:
    mate_depth = len(pv.moves_san) // 2 + 1
    if mate_depth <= 1:
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})
    return I18nMessage(
        key="explanation.best.pv_mate",
        params={
            "san": san,
            "moves": str(mate_depth),
            "line": _format_line(pv.moves_san),
        },
    )


def _explain_pv_sacrifice(
    san: str, pv: PVAnalysis, tactical_pattern: str | None
) -> I18nMessage:
    assert pv.net_piece_won is not None
    piece_key = _type_key(pv.net_piece_won, "acc")
    line_str = _format_line(pv.moves_san)
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
    return pv.balance_gain >= _piece_value(pv.net_piece_won)


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
            "piece": _type_key(pv.net_piece_won, "acc"),
            "line": _format_line(pv.moves_san),
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


# ---------------------------------------------------------------------------
# Blunder-side explanation
# ---------------------------------------------------------------------------


def _blunder_missed_mate(
    board: chess.Board, best_move: chess.Move | None, **_: object
) -> I18nMessage | None:
    if best_move and _move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.blunder.missed_mate")
    return None


def _blunder_hanging(
    board: chess.Board,
    blunder_move: chess.Move,
    board_after: chess.Board,
    player_color: chess.Color,
    moved_key_nom: str,
    **_: object,
) -> I18nMessage | None:
    if not _is_hanging(board_after, blunder_move.to_square, player_color):
        return None
    return I18nMessage(
        key="explanation.blunder.hanging_piece",
        params={
            "piece": moved_key_nom,
            "square": chess.square_name(blunder_move.to_square),
        },
    )


def _is_newly_exposed(
    board: chess.Board,
    board_after: chess.Board,
    sq: chess.Square,
    blunder_move_to: chess.Square,
    player_color: chess.Color,
) -> bool:
    piece = board_after.piece_at(sq)
    if piece is None or piece.color != player_color or sq == blunder_move_to:
        return False
    return _is_hanging(board_after, sq, player_color) and not _is_hanging(
        board, sq, player_color
    )


def _find_exposed_piece(
    board: chess.Board,
    board_after: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    for sq in chess.SQUARES:
        if not _is_newly_exposed(
            board, board_after, sq, blunder_move.to_square, player_color
        ):
            continue
        piece = board_after.piece_at(sq)
        assert piece is not None
        return (piece.piece_type, sq)
    return None


def _blunder_exposed(
    board: chess.Board,
    board_after: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    moved_key_inst: str | None,
    **_: object,
) -> I18nMessage | None:
    if moved_key_inst is None:
        return None
    exposed = _find_exposed_piece(board, board_after, blunder_move, player_color)
    if exposed is None:
        return None
    piece_type, sq = exposed
    return I18nMessage(
        key="explanation.blunder.exposed_piece",
        params={
            "piece": moved_key_inst,
            "exposed": _type_key(piece_type, "acc"),
            "square": chess.square_name(sq),
        },
    )


def _blunder_ignored_threat(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    **_: object,
) -> I18nMessage | None:
    ignored = _find_ignored_threat(board, blunder_move, player_color)
    if ignored is None:
        return None
    piece_type, ignored_sq = ignored
    return I18nMessage(
        key="explanation.blunder.ignored_threat",
        params={
            "piece": _type_key(piece_type, "acc"),
            "square": chess.square_name(ignored_sq),
        },
    )


def _blunder_bad_capture(
    board: chess.Board,
    blunder_move: chess.Move,
    board_after: chess.Board,
    player_color: chess.Color,
    moved_key_inst: str | None,
    **_: object,
) -> I18nMessage | None:
    if moved_key_inst is None or not board.is_capture(blunder_move):
        return None
    captured = board.piece_at(blunder_move.to_square)
    mover = board.piece_at(blunder_move.from_square)
    if not (captured and mover):
        return None
    if _piece_value(mover.piece_type) <= _piece_value(captured.piece_type):
        return None
    if not board_after.is_attacked_by(not player_color, blunder_move.to_square):
        return None
    return I18nMessage(
        key="explanation.blunder.bad_capture",
        params={"piece": moved_key_inst},
    )


def _blunder_cp_loss(cp_loss: int, **_: object) -> I18nMessage | None:
    pawn_loss = cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss < 1:
        return None
    return I18nMessage(
        key="explanation.blunder.cp_loss",
        params={"loss": f"{pawn_loss:.1f}"},
    )


_BLUNDER_STRATEGIES: tuple[Callable[..., I18nMessage | None], ...] = (
    _blunder_missed_mate,
    _blunder_hanging,
    _blunder_exposed,
    _blunder_ignored_threat,
    _blunder_bad_capture,
    _blunder_cp_loss,
)


def _explain_blunder(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    cp_loss: int,
    best_move: chess.Move | None = None,
) -> I18nMessage | None:
    moved_key_nom = _piece_key(board, blunder_move.from_square)
    if not moved_key_nom:
        return None
    board_after = board.copy()
    board_after.push(blunder_move)
    ctx = {
        "board": board,
        "blunder_move": blunder_move,
        "board_after": board_after,
        "player_color": player_color,
        "cp_loss": cp_loss,
        "best_move": best_move,
        "moved_key_nom": moved_key_nom,
        "moved_key_inst": _piece_key(board, blunder_move.from_square, "inst"),
    }
    for strategy in _BLUNDER_STRATEGIES:
        message = strategy(**ctx)
        if message is not None:
            return message
    return None


# ---------------------------------------------------------------------------
# Best-move explanation (static fallbacks)
# ---------------------------------------------------------------------------

_PATTERN_KEYS = MappingProxyType(
    {
        "fork": "explanation.best.pattern_fork",
        "pin": "explanation.best.pattern_pin",
        "skewer": "explanation.best.pattern_skewer",
        "back rank threat": "explanation.best.pattern_back_rank",
        "hanging piece": "explanation.best.pattern_hanging",
    }
)

_THREAT_KEYS = MappingProxyType(
    {
        _THREAT_MATE: "explanation.best.threatens_mate",
        _THREAT_CAPTURE_CHECK: "explanation.best.threatens_capture_check",
        _THREAT_PIECE: "explanation.best.creates_threat",
        _THREAT_ATTACKS: "explanation.best.attacks_piece",
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
                params={"san": san, "piece": _type_key(captured.piece_type, "acc")},
            )
    if not _has_pattern(tactical_pattern):
        return I18nMessage(key="explanation.best.check_winning", params={"san": san})

    if tactical_pattern.lower() == "hanging piece":
        hanging = _find_hanging_piece(board, best_move, board.turn)
        if hanging is not None:
            piece_type, sq = hanging
            return I18nMessage(
                key="explanation.best.check_wins_hanging",
                params={
                    "san": san,
                    "piece": _type_key(piece_type, "acc"),
                    "square": chess.square_name(sq),
                },
            )
    return I18nMessage(
        key="explanation.best.check_with_pattern",
        params={"san": san, "pattern": tactical_pattern.lower()},
    )


def _is_capturable_hanging(
    board: chess.Board, best_move: chess.Move, captured: chess.Piece | None
) -> bool:
    if captured is None or not board.is_capture(best_move):
        return False
    return _is_hanging(board, best_move.to_square, not board.turn)


def _explain_best_pattern(
    board: chess.Board,
    best_move: chess.Move,
    san: str,
    tactical_pattern: str,
) -> I18nMessage | None:
    pattern_lower = tactical_pattern.lower()
    if "discovered" in pattern_lower:
        return I18nMessage(
            key="explanation.best.pattern_discovered", params={"san": san}
        )
    if pattern_lower == "hanging piece":
        captured = board.piece_at(best_move.to_square)
        if _is_capturable_hanging(board, best_move, captured):
            assert captured is not None
            return I18nMessage(
                key="explanation.best.pattern_hanging_piece",
                params={
                    "san": san,
                    "piece": _type_key(captured.piece_type, "acc"),
                    "square": chess.square_name(best_move.to_square),
                },
            )
        return None
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
    if captured is None:
        return None
    return I18nMessage(
        key="explanation.best.wins_piece",
        params={"san": san, "piece": _type_key(captured.piece_type, "acc")},
    )


def _explain_best_threat(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    threat = _detect_next_move_threat(board, best_move)
    if threat is None:
        return None
    return I18nMessage(
        key=_THREAT_KEYS[threat.kind],
        params={"san": san, "piece": threat.piece_key},
    )


def _explain_best_retreat(
    board: chess.Board, best_move: chess.Move, san: str
) -> I18nMessage | None:
    retreat = _is_retreat_to_safety(board, best_move)
    if retreat is None:
        return None
    piece_type, _from_sq = retreat
    return I18nMessage(
        key="explanation.best.saves_piece",
        params={"san": san, "piece": _type_key(piece_type, "acc")},
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
) -> I18nMessage | None:
    if _has_pattern(tactical_pattern):
        pattern_msg = _explain_best_pattern(board, best_move, san, tactical_pattern)
        if pattern_msg is not None:
            return pattern_msg
    retreat = _explain_best_retreat(board, best_move, san)
    if retreat is not None:
        return retreat
    capture = _explain_best_capture(board, best_move, san)
    if capture is not None:
        return capture
    return _explain_best_threat(board, best_move, san)


def _explain_best_static(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
) -> I18nMessage | None:
    """Fallback explanation using only static position analysis (no PV)."""
    san = board.san(best_move)
    if _move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})
    if _move_gives_check(board, best_move):
        return _explain_best_check(board, best_move, san, tactical_pattern)
    static_msg = _try_static_strategies(board, best_move, san, tactical_pattern)
    if static_msg is not None:
        return static_msg
    return _explain_best_loss_avoidance(san, cp_loss)


# ---------------------------------------------------------------------------
# Best-move explanation (PV-first, with static fallback)
# ---------------------------------------------------------------------------


def _explain_best(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
    best_line: list[str] | None = None,
) -> I18nMessage | None:
    if _move_gives_mate(board, best_move):
        return I18nMessage(
            key="explanation.best.checkmate", params={"san": board.san(best_move)}
        )

    if best_line and len(best_line) >= 2:
        pv = _analyze_pv(board, best_move, best_line)
        if pv:
            pv_msg = _explain_best_from_pv(board, best_move, pv, tactical_pattern)
            if pv_msg:
                return pv_msg

    return _explain_best_static(board, best_move, tactical_pattern, cp_loss)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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


def generate_explanation(
    fen: str,
    blunder_uci: str,
    best_move_uci: str | None,
    tactical_pattern: str | None = None,
    cp_loss: int = 0,
    best_line: list[str] | None = None,
) -> BlunderExplanation:
    board = chess.Board(fen)
    blunder_move = _parse_legal_move(board, blunder_uci)
    if blunder_move is None:
        return BlunderExplanation(blunder=None, best_move=None)

    best_move = _parse_legal_move(board, best_move_uci)
    blunder_msg = _explain_blunder(board, blunder_move, board.turn, cp_loss, best_move)
    best_msg = (
        _explain_best(board, best_move, tactical_pattern, cp_loss, best_line)
        if best_move
        else None
    )
    return BlunderExplanation(blunder=blunder_msg, best_move=best_msg)

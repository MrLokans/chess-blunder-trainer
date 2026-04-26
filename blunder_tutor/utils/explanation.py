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
                value = PIECE_VALUES.get(piece.piece_type, 0)
                results.append((sq, piece.piece_type, value))
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


def _find_hanging_piece(
    board: chess.Board,
    move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(move)
    enemy = not player_color
    best: tuple[int, chess.PieceType, chess.Square] | None = None
    for sq in chess.SQUARES:
        piece = board_after.piece_at(sq)
        if (
            piece
            and piece.color == enemy
            and piece.piece_type != chess.KING
            and _is_hanging(board_after, sq, enemy)
        ):
            value = PIECE_VALUES.get(piece.piece_type, 0)
            if best is None or value > best[0]:
                best = (value, piece.piece_type, sq)
    if best is None:
        return None
    return (best[1], best[2])


def _find_ignored_threat(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(blunder_move)
    enemy = not player_color

    best: tuple[int, chess.PieceType, chess.Square] | None = None
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if (
            piece is None
            or piece.color != player_color
            or piece.piece_type == chess.KING
        ):
            continue
        piece_val = PIECE_VALUES.get(piece.piece_type, 0)
        if piece_val < 3:
            continue

        if blunder_move.from_square == sq:
            continue

        attackers_before = board.attackers(enemy, sq)
        if not attackers_before:
            continue
        min_attacker_val = min(
            PIECE_VALUES.get(board.piece_at(a).piece_type, 0)
            for a in attackers_before
            if board.piece_at(a)
        )
        if min_attacker_val >= piece_val:
            continue

        if (
            board.is_capture(blunder_move)
            and blunder_move.to_square in attackers_before
        ):
            continue

        piece_after = board_after.piece_at(sq)
        if piece_after is None or piece_after.color != player_color:
            continue
        if not board_after.is_attacked_by(enemy, sq):
            continue

        if best is None or piece_val > best[0]:
            best = (piece_val, piece.piece_type, sq)

    if best is None:
        return None
    return (best[1], best[2])


def _is_retreat_to_safety(
    board: chess.Board,
    best_move: chess.Move,
) -> tuple[chess.PieceType, chess.Square] | None:
    if board.is_capture(best_move):
        return None

    player = board.turn
    enemy = not player
    piece = board.piece_at(best_move.from_square)
    if piece is None or piece.color != player or piece.piece_type == chess.KING:
        return None

    piece_val = PIECE_VALUES.get(piece.piece_type, 0)
    if piece_val < 3:
        return None

    attackers = board.attackers(enemy, best_move.from_square)
    if not attackers:
        return None
    min_attacker_val = min(
        PIECE_VALUES.get(board.piece_at(a).piece_type, 0)
        for a in attackers
        if board.piece_at(a)
    )
    if min_attacker_val >= piece_val:
        return None

    board_after = board.copy()
    board_after.push(best_move)
    dest_attackers = board_after.attackers(enemy, best_move.to_square)
    for a in dest_attackers:
        attacker_piece = board_after.piece_at(a)
        if (
            attacker_piece
            and PIECE_VALUES.get(attacker_piece.piece_type, 0) < piece_val
        ):
            return None

    return (piece.piece_type, best_move.from_square)


def _count_material(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            total += PIECE_VALUES.get(piece.piece_type, 0)
    return total


def _material_balance(board: chess.Board, color: chess.Color) -> int:
    return _count_material(board, color) - _count_material(board, not color)


# ---------------------------------------------------------------------------
# PV (principal variation) analysis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PVCapture:
    piece_type: chess.PieceType
    by_color: chess.Color


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


def _analyze_pv(
    board: chess.Board,
    best_move: chess.Move,
    best_line: list[str],
) -> PVAnalysis | None:
    player = board.turn
    line_board = board.copy()
    balance_before = _material_balance(board, player)

    player_caps: list[_PVCapture] = []
    opp_caps: list[_PVCapture] = []
    gives_check = False
    gives_mate = False

    try:
        line_board.push(best_move)
        if line_board.is_checkmate():
            gives_mate = True
        gives_check = line_board.is_check()

        if board.is_capture(best_move):
            captured = board.piece_at(best_move.to_square)
            if captured:
                player_caps.append(_PVCapture(captured.piece_type, player))

        for move_san in best_line[1:]:
            prev_board = line_board.copy()
            move = line_board.parse_san(move_san)
            is_cap = line_board.is_capture(move)
            side = line_board.turn
            line_board.push(move)

            if is_cap:
                captured = prev_board.piece_at(move.to_square)
                if captured:
                    cap = _PVCapture(captured.piece_type, side)
                    if side == player:
                        player_caps.append(cap)
                    else:
                        opp_caps.append(cap)

            if line_board.is_checkmate():
                gives_mate = True
                break
    except (ValueError, chess.IllegalMoveError):
        if not player_caps and not gives_check:
            return None

    balance_after = _material_balance(line_board, player)

    best_opp_loss: chess.PieceType | None = None
    if player_caps:
        best_opp_loss = max(
            (c.piece_type for c in player_caps),
            key=lambda pt: PIECE_VALUES.get(pt, 0),
        )

    return PVAnalysis(
        moves_san=best_line,
        gives_check=gives_check,
        gives_mate=gives_mate,
        balance_gain=balance_after - balance_before,
        player_captures=player_caps,
        opponent_captures=opp_caps,
        best_opponent_loss=best_opp_loss,
    )


def _format_line(moves: list[str], max_moves: int = 5) -> str:
    return " ".join(moves[:max_moves])


def _explain_best_from_pv(
    board: chess.Board,
    best_move: chess.Move,
    pv: PVAnalysis,
    tactical_pattern: str | None,
) -> I18nMessage | None:
    san = board.san(best_move)
    line_str = _format_line(pv.moves_san)

    # Mate in the PV
    if pv.gives_mate:
        mate_depth = len(pv.moves_san) // 2 + 1
        if mate_depth <= 1:
            return I18nMessage(key="explanation.best.checkmate", params={"san": san})  # noqa: WPS204 — single-key params dict; building a helper for one literal would obscure intent.
        return I18nMessage(
            key="explanation.best.pv_mate",
            params={"san": san, "moves": str(mate_depth), "line": line_str},
        )

    # Sacrifice that wins material through a combination
    if pv.is_sacrifice_combination and pv.net_piece_won:
        piece_key = _type_key(pv.net_piece_won, "acc")
        pattern_suffix = ""
        if _has_pattern(tactical_pattern):
            pattern_suffix = tactical_pattern.lower()
        if pattern_suffix:
            return I18nMessage(
                key="explanation.best.pv_wins_piece_via_pattern",
                params={
                    "san": san,
                    "piece": piece_key,
                    "pattern": pattern_suffix,
                    "line": line_str,
                },
            )
        return I18nMessage(
            key="explanation.best.pv_wins_piece_via_combination",
            params={"san": san, "piece": piece_key, "line": line_str},
        )

    # Non-sacrifice that wins material (net gain ≥ 1 pawn)
    if pv.balance_gain >= 1 and pv.net_piece_won:
        piece_key = _type_key(pv.net_piece_won, "acc")
        # Simple first-move capture that wins the piece directly
        if (
            board.is_capture(best_move)
            and len(pv.player_captures) == 1
            and pv.balance_gain >= PIECE_VALUES.get(pv.net_piece_won, 0)
        ):
            return None  # Let static analysis handle simple captures
        return I18nMessage(
            key="explanation.best.pv_wins_piece",
            params={"san": san, "piece": piece_key, "line": line_str},
        )

    # Material gain without a clear piece (e.g. wins 2 pawns through trades)
    if pv.balance_gain >= 3:
        return I18nMessage(
            key="explanation.best.combination",
            params={"san": san},
        )

    return None


# ---------------------------------------------------------------------------
# Blunder-side explanation
# ---------------------------------------------------------------------------


def _explain_blunder(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    cp_loss: int,
    best_move: chess.Move | None = None,
) -> I18nMessage | None:
    board_after = board.copy()
    board_after.push(blunder_move)

    if best_move and _move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.blunder.missed_mate")

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

    # Ignored threat — a friendly piece (value ≥ 3) is under profitable attack
    # both before and after the blunder, and the blunder doesn't address it
    ignored = _find_ignored_threat(board, blunder_move, player_color)
    if ignored:
        piece_type, ignored_sq = ignored
        return I18nMessage(
            key="explanation.blunder.ignored_threat",
            params={
                "piece": _type_key(piece_type, "acc"),
                "square": chess.square_name(ignored_sq),
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


def _explain_best_static(
    board: chess.Board,
    best_move: chess.Move,
    tactical_pattern: str | None,
    cp_loss: int,
) -> I18nMessage | None:
    """Fallback explanation using only static position analysis (no PV)."""
    san = board.san(best_move)

    if _move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})  # noqa: WPS204 — single-key params dict; building a helper for one literal would obscure intent.

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
            if tactical_pattern.lower() == "hanging piece":
                hanging = _find_hanging_piece(board, best_move, board.turn)
                if hanging:
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
        return I18nMessage(key="explanation.best.check_winning", params={"san": san})

    if _has_pattern(tactical_pattern):
        pattern_lower = tactical_pattern.lower()
        if "discovered" in pattern_lower:
            return I18nMessage(
                key="explanation.best.pattern_discovered", params={"san": san}
            )
        if pattern_lower == "hanging piece":
            if board.is_capture(best_move):
                captured = board.piece_at(best_move.to_square)
                if captured and _is_hanging(board, best_move.to_square, not board.turn):
                    return I18nMessage(
                        key="explanation.best.pattern_hanging_piece",
                        params={
                            "san": san,
                            "piece": _type_key(captured.piece_type, "acc"),
                            "square": chess.square_name(best_move.to_square),
                        },
                    )
        else:
            pattern_key = _PATTERN_KEYS.get(pattern_lower)
            if pattern_key:
                return I18nMessage(key=pattern_key, params={"san": san})
            return I18nMessage(
                key="explanation.best.pattern_generic",
                params={"san": san, "pattern": pattern_lower},
            )

    # Retreat to safety — best move saves a piece from profitable attack
    retreat = _is_retreat_to_safety(board, best_move)
    if retreat:
        piece_type, _from_sq = retreat
        return I18nMessage(
            key="explanation.best.saves_piece",
            params={
                "san": san,
                "piece": _type_key(piece_type, "acc"),
            },
        )

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

    pawn_loss = cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss >= SIGNIFICANT_PAWN_LOSS:
        return I18nMessage(
            key="explanation.best.avoids_loss",
            params={"san": san, "loss": f"{pawn_loss:.1f}"},
        )

    return I18nMessage(key="explanation.best.fallback", params={"san": san})


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
    # Phase 1: immediate mate (no PV needed)
    if _move_gives_mate(board, best_move):
        san = board.san(best_move)
        return I18nMessage(key="explanation.best.checkmate", params={"san": san})

    # Phase 2: PV-first — walk the engine line to explain what happens
    if best_line and len(best_line) >= 2:
        pv = _analyze_pv(board, best_move, best_line)
        if pv:
            pv_msg = _explain_best_from_pv(board, best_move, pv, tactical_pattern)
            if pv_msg:
                return pv_msg

    # Phase 3: static fallback (pattern detection, simple captures, threats)
    return _explain_best_static(board, best_move, tactical_pattern, cp_loss)


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

    best_move: chess.Move | None = None
    best_msg = None
    if best_move_uci:
        try:
            best_move = chess.Move.from_uci(best_move_uci)
            if best_move not in board.legal_moves:
                best_move = None
        except ValueError:
            pass

    blunder_msg = _explain_blunder(
        board, blunder_move, player_color, cp_loss, best_move
    )

    if best_move:
        best_msg = _explain_best(board, best_move, tactical_pattern, cp_loss, best_line)

    return BlunderExplanation(blunder=blunder_msg, best_move=best_msg)

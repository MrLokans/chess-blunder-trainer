"""Tactical pattern detection for chess positions.

Detects common tactical motifs like forks, pins, skewers, discovered attacks,
back rank weaknesses, and more. Used to classify blunders by pattern type.

The key insight for blunder classification:
1. MISSED TACTIC - The best move exploited a tactic we didn't see
2. ALLOWED TACTIC - Our blunder let the opponent execute a tactic against us
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from types import MappingProxyType

import chess


class TacticalPattern(IntEnum):
    NONE = 0
    FORK = 1
    PIN = 2
    SKEWER = 3
    DISCOVERED_ATTACK = 4
    DISCOVERED_CHECK = 5
    DOUBLE_CHECK = 6
    BACK_RANK_THREAT = 7
    TRAPPED_PIECE = 8
    HANGING_PIECE = 9
    REMOVAL_OF_DEFENDER = 10
    OVERLOADED_PIECE = 11


# Tactical pattern detection thresholds. Material gain in centipawns:
# 300 ≈ minor piece, 500 ≈ rook (used for "is this discovered attack
# substantial?"); 10000 represents mate-threat-level severity for the
# back-rank weight.
DISCOVERED_ATTACK_MATERIAL_FLOOR = 300
DOUBLE_CHECK_MATERIAL_GAIN = 500
MATE_THREAT_MATERIAL_GAIN = 10_000


PATTERN_LABELS = MappingProxyType(
    {
        TacticalPattern.NONE: "None",
        TacticalPattern.FORK: "Fork",
        TacticalPattern.PIN: "Pin",
        TacticalPattern.SKEWER: "Skewer",
        TacticalPattern.DISCOVERED_ATTACK: "Discovered Attack",
        TacticalPattern.DISCOVERED_CHECK: "Discovered Check",
        TacticalPattern.DOUBLE_CHECK: "Double Check",
        TacticalPattern.BACK_RANK_THREAT: "Back Rank Threat",
        TacticalPattern.TRAPPED_PIECE: "Trapped Piece",
        TacticalPattern.HANGING_PIECE: "Hanging Piece",
        TacticalPattern.REMOVAL_OF_DEFENDER: "Removal of Defender",
        TacticalPattern.OVERLOADED_PIECE: "Overloaded Piece",
    }
)

# Standard piece values in centipawns
PIECE_VALUES = MappingProxyType(
    {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20000,
    }
)


@dataclass
class TacticalMotif:
    pattern: TacticalPattern
    description: str
    squares: list[chess.Square] = field(default_factory=list)
    pieces: list[chess.PieceType] = field(default_factory=list)
    material_gain: int = 0


@dataclass
class BlunderTactics:
    """Tactical analysis of a blunder position."""

    missed_tactic: TacticalMotif | None = None
    allowed_tactic: TacticalMotif | None = None
    blunder_reason: str = ""

    @property
    def primary_pattern(self) -> TacticalPattern:
        if self.missed_tactic and self.missed_tactic.material_gain > 0:
            return self.missed_tactic.pattern
        if self.allowed_tactic and self.allowed_tactic.material_gain > 0:
            return self.allowed_tactic.pattern
        if self.missed_tactic:
            return self.missed_tactic.pattern
        if self.allowed_tactic:
            return self.allowed_tactic.pattern
        return TacticalPattern.NONE

    @property
    def primary_pattern_name(self) -> str:
        return PATTERN_LABELS[self.primary_pattern]


def _get_piece_value(piece_type: chess.PieceType | None) -> int:
    if piece_type is None:
        return 0
    return PIECE_VALUES.get(piece_type, 0)


def _square_distance(sq1: chess.Square, sq2: chess.Square) -> int:
    file1, rank1 = chess.square_file(sq1), chess.square_rank(sq1)
    file2, rank2 = chess.square_file(sq2), chess.square_rank(sq2)
    return max(abs(file1 - file2), abs(rank1 - rank2))


def _count_attacked_valuable_pieces(
    board: chess.Board,
    attacker_square: chess.Square,
    attacker_color: chess.Color,
    min_value: int = 0,
) -> list[tuple[chess.Square, chess.PieceType, int]]:
    attacks = board.attacks(attacker_square)
    enemy_color = not attacker_color
    attacked = []
    for sq in chess.SQUARES:
        if not (attacks & chess.BB_SQUARES[sq]):
            continue
        piece = board.piece_at(sq)
        if piece and piece.color == enemy_color:
            value = _get_piece_value(piece.piece_type)
            if value >= min_value:
                attacked.append((sq, piece.piece_type, value))
    return attacked


def _fork_description(
    targets: list[tuple[chess.Square, chess.PieceType, int]],
) -> str:
    piece_types = {pt for _, pt, _ in targets}
    if chess.KING in piece_types and chess.QUEEN in piece_types:
        return "Royal Fork (King + Queen)"
    if chess.KING in piece_types:
        return f"Fork with Check ({len(targets)} pieces)"
    piece_names = [chess.piece_name(pt) for _, pt, _ in targets[:2]]
    return f"Fork ({' + '.join(piece_names)})"


def _filter_fork_targets(
    attacked: list[tuple[chess.Square, chess.PieceType, int]],
    attacker_value: int,
) -> list[tuple[chess.Square, chess.PieceType, int]]:
    return [
        target
        for target in attacked
        if target[2] >= attacker_value or target[1] == chess.KING
    ]


def _build_fork_motif(
    targets: list[tuple[chess.Square, chess.PieceType, int]],
    attack_sq: chess.Square,
) -> TacticalMotif:
    values = sorted((value for _, _, value in targets), reverse=True)
    return TacticalMotif(
        pattern=TacticalPattern.FORK,
        description=_fork_description(targets),
        squares=[attack_sq] + [sq for sq, _, _ in targets],
        pieces=[pt for _, pt, _ in targets],
        material_gain=values[1] if len(values) > 1 else values[0],
    )


def detect_fork(board: chess.Board, move: chess.Move) -> TacticalMotif | None:
    """Detect if a move creates a fork (attacks 2+ valuable pieces)."""
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None
    board_after = board.copy()
    board_after.push(move)
    attacked = _count_attacked_valuable_pieces(
        board_after, move.to_square, moving_piece.color
    )
    valuable_targets = _filter_fork_targets(
        attacked, _get_piece_value(moving_piece.piece_type)
    )
    if len(valuable_targets) < 2:
        return None
    return _build_fork_motif(valuable_targets, move.to_square)


def _find_pinner(
    board: chess.Board, pin_mask: chess.Bitboard, enemy_color: chess.Color
) -> chess.Square | None:
    for pinner_sq in chess.SQUARES:
        if not (pin_mask & chess.BB_SQUARES[pinner_sq]):
            continue
        pinner = board.piece_at(pinner_sq)
        if pinner and pinner.color == enemy_color:
            return pinner_sq
    return None


def _detect_absolute_pins(
    board: chess.Board, color: chess.Color
) -> list[TacticalMotif]:
    enemy_color = not color
    pins: list[TacticalMotif] = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not (piece and piece.color == color and board.is_pinned(color, sq)):
            continue
        pinner_sq = _find_pinner(board, board.pin(color, sq), enemy_color)
        if pinner_sq is None:
            continue
        pins.append(
            TacticalMotif(
                pattern=TacticalPattern.PIN,
                description=f"Absolute Pin ({chess.piece_name(piece.piece_type)} to King)",
                squares=[sq, pinner_sq],
                pieces=[piece.piece_type],
                material_gain=_get_piece_value(piece.piece_type),
            )
        )
    return pins


def _is_pinning_attacker(piece: chess.Piece | None, enemy_color: chess.Color) -> bool:
    if piece is None or piece.color != enemy_color:
        return False
    return piece.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN)


def _is_pin_behind(
    board: chess.Board,
    behind_sq: chess.Square,
    attacker_sq: chess.Square,
    target_sq: chess.Square,
    ray: chess.Bitboard,
    target_dist: int,
    color: chess.Color,
) -> bool:
    if behind_sq in (attacker_sq, target_sq):
        return False
    if not (ray & chess.BB_SQUARES[behind_sq]):
        return False
    if _square_distance(attacker_sq, behind_sq) <= target_dist:
        return False
    behind = board.piece_at(behind_sq)
    return bool(behind and behind.color == color and behind.piece_type != chess.KING)


def _find_relative_pin_behind(
    board: chess.Board,
    attacker_sq: chess.Square,
    target_sq: chess.Square,
    color: chess.Color,
) -> chess.Square | None:
    """Find a friendly piece behind `target_sq` that's pinned through it."""
    ray = chess.ray(attacker_sq, target_sq)
    if not ray:
        return None
    target_dist = _square_distance(attacker_sq, target_sq)
    for behind_sq in chess.SQUARES:
        if _is_pin_behind(
            board, behind_sq, attacker_sq, target_sq, ray, target_dist, color
        ):
            return behind_sq
    return None


def _is_duplicate_pin(
    pins: list[TacticalMotif], target_sq: chess.Square, attacker_sq: chess.Square
) -> bool:
    return any(target_sq in p.squares and attacker_sq in p.squares for p in pins)


def _scan_pinner_targets(
    board: chess.Board,
    attacker_sq: chess.Square,
    color: chess.Color,
    pins: list[TacticalMotif],
) -> None:
    attacks = board.attacks(attacker_sq)
    for target_sq in chess.SQUARES:
        if not (attacks & chess.BB_SQUARES[target_sq]):
            continue
        target = board.piece_at(target_sq)
        if not target or target.color != color:
            continue
        motif = _try_relative_pin(board, attacker_sq, target_sq, target, color, pins)
        if motif is not None:
            pins.append(motif)


def _detect_relative_pins(
    board: chess.Board, color: chess.Color
) -> list[TacticalMotif]:
    enemy_color = not color
    pins: list[TacticalMotif] = []
    for attacker_sq in chess.SQUARES:
        if _is_pinning_attacker(board.piece_at(attacker_sq), enemy_color):
            _scan_pinner_targets(board, attacker_sq, color, pins)
    return pins


def _try_relative_pin(
    board: chess.Board,
    attacker_sq: chess.Square,
    target_sq: chess.Square,
    target: chess.Piece,
    color: chess.Color,
    existing_pins: list[TacticalMotif],
) -> TacticalMotif | None:
    behind_sq = _find_relative_pin_behind(board, attacker_sq, target_sq, color)
    if behind_sq is None:
        return None
    behind = board.piece_at(behind_sq)
    if behind is None:
        return None
    target_value = _get_piece_value(target.piece_type)
    if _get_piece_value(behind.piece_type) <= target_value:
        return None
    if _is_duplicate_pin(existing_pins, target_sq, attacker_sq):
        return None
    return TacticalMotif(
        pattern=TacticalPattern.PIN,
        description=f"Relative Pin ({chess.piece_name(target.piece_type)} to {chess.piece_name(behind.piece_type)})",
        squares=[target_sq, attacker_sq, behind_sq],
        pieces=[target.piece_type, behind.piece_type],
        material_gain=target_value,
    )


def detect_pin(board: chess.Board, color: chess.Color) -> list[TacticalMotif]:
    """Detect all pins against a given color (both absolute and relative)."""
    return _detect_absolute_pins(board, color) + _detect_relative_pins(board, color)


def _is_skewer_behind(
    board_after: chess.Board,
    behind_sq: chess.Square,
    attack_origin: chess.Square,
    front_sq: chess.Square,
    ray: chess.Bitboard,
    front_dist: int,
    enemy_color: chess.Color,
) -> bool:
    if behind_sq in (front_sq, attack_origin):
        return False
    if not (ray & chess.BB_SQUARES[behind_sq]):
        return False
    if _square_distance(attack_origin, behind_sq) <= front_dist:
        return False
    behind = board_after.piece_at(behind_sq)
    return bool(behind and behind.color == enemy_color)


def _find_skewer_behind(
    board_after: chess.Board,
    attack_origin: chess.Square,
    front_sq: chess.Square,
    enemy_color: chess.Color,
) -> chess.Square | None:
    ray = chess.ray(attack_origin, front_sq)
    front_dist = _square_distance(attack_origin, front_sq)
    for behind_sq in chess.SQUARES:
        if _is_skewer_behind(
            board_after,
            behind_sq,
            attack_origin,
            front_sq,
            ray,
            front_dist,
            enemy_color,
        ):
            return behind_sq
    return None


def _try_skewer(
    board_after: chess.Board,
    attack_origin: chess.Square,
    front_sq: chess.Square,
    front_piece: chess.Piece,
    enemy_color: chess.Color,
) -> TacticalMotif | None:
    if front_piece.piece_type not in (chess.KING, chess.QUEEN, chess.ROOK):
        return None
    behind_sq = _find_skewer_behind(board_after, attack_origin, front_sq, enemy_color)
    if behind_sq is None:
        return None
    behind = board_after.piece_at(behind_sq)
    if behind is None:
        return None
    front_value = _get_piece_value(front_piece.piece_type)
    behind_value = _get_piece_value(behind.piece_type)
    if front_value <= behind_value:
        return None
    return TacticalMotif(
        pattern=TacticalPattern.SKEWER,
        description=f"Skewer ({chess.piece_name(front_piece.piece_type)} to {chess.piece_name(behind.piece_type)})",
        squares=[attack_origin, front_sq, behind_sq],
        pieces=[front_piece.piece_type, behind.piece_type],
        material_gain=behind_value,
    )


def detect_skewer(board: chess.Board, move: chess.Move) -> TacticalMotif | None:
    """Detect if a move creates a skewer."""
    moving_piece = board.piece_at(move.from_square)
    if moving_piece is None:
        return None
    if moving_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return None

    board_after = board.copy()
    board_after.push(move)
    enemy_color = not moving_piece.color
    attacks = board_after.attacks(move.to_square)

    for sq in chess.SQUARES:
        if not (attacks & chess.BB_SQUARES[sq]):
            continue
        front_piece = board_after.piece_at(sq)
        if not front_piece or front_piece.color != enemy_color:
            continue
        skewer = _try_skewer(board_after, move.to_square, sq, front_piece, enemy_color)
        if skewer is not None:
            return skewer
    return None


def _is_potential_discoverer(
    piece: chess.Piece | None,
    attacker_color: chess.Color,
    sq: chess.Square,
    move_to: chess.Square,
) -> bool:
    if not piece or piece.color != attacker_color:
        return False
    if sq == move_to:
        return False
    return piece.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN)


def _build_discovered_motif(
    attacker_sq: chess.Square,
    attacker_piece: chess.Piece,
    move_from: chess.Square,
    target_sq: chess.Square,
    target_piece: chess.Piece,
) -> TacticalMotif | None:
    target_value = _get_piece_value(target_piece.piece_type)
    if target_piece.piece_type == chess.KING:
        return TacticalMotif(
            pattern=TacticalPattern.DISCOVERED_CHECK,
            description=f"Discovered Check (by {chess.piece_name(attacker_piece.piece_type)})",
            squares=[attacker_sq, move_from, target_sq],
            pieces=[attacker_piece.piece_type],
            material_gain=target_value,
        )
    if target_value >= DISCOVERED_ATTACK_MATERIAL_FLOOR:
        return TacticalMotif(
            pattern=TacticalPattern.DISCOVERED_ATTACK,
            description=f"Discovered Attack on {chess.piece_name(target_piece.piece_type)}",
            squares=[attacker_sq, move_from, target_sq],
            pieces=[attacker_piece.piece_type, target_piece.piece_type],
            material_gain=target_value,
        )
    return None


def _try_discovered_attack(
    board: chess.Board,
    board_after: chess.Board,
    attacker_sq: chess.Square,
    attacker_piece: chess.Piece,
    move: chess.Move,
    enemy_color: chess.Color,
) -> TacticalMotif | None:
    if not chess.ray(attacker_sq, move.from_square):
        return None
    new_attacks = board_after.attacks(attacker_sq) & ~board.attacks(attacker_sq)
    for target_sq in chess.SQUARES:
        if not (new_attacks & chess.BB_SQUARES[target_sq]):
            continue
        target = board_after.piece_at(target_sq)
        if target and target.color == enemy_color:
            motif = _build_discovered_motif(
                attacker_sq, attacker_piece, move.from_square, target_sq, target
            )
            if motif is not None:
                return motif
    return None


def detect_discovered_attack(
    board: chess.Board, move: chess.Move
) -> TacticalMotif | None:
    """Detect if moving a piece reveals an attack from a piece behind it."""
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None

    board_after = board.copy()
    board_after.push(move)
    enemy_color = not moving_piece.color

    for attacker_sq in chess.SQUARES:
        attacker = board.piece_at(attacker_sq)
        if not _is_potential_discoverer(
            attacker, moving_piece.color, attacker_sq, move.to_square
        ):
            continue
        assert attacker is not None
        motif = _try_discovered_attack(
            board, board_after, attacker_sq, attacker, move, enemy_color
        )
        if motif is not None:
            return motif
    return None


def detect_double_check(board: chess.Board, move: chess.Move) -> TacticalMotif | None:
    """Detect if a move delivers double check."""
    board_after = board.copy()
    board_after.push(move)
    if not board_after.is_check():
        return None

    checkers = board_after.checkers()
    if bin(checkers).count("1") < 2:
        return None

    checker_squares = [sq for sq in chess.SQUARES if checkers & chess.BB_SQUARES[sq]]
    return TacticalMotif(
        pattern=TacticalPattern.DOUBLE_CHECK,
        description="Double Check",
        squares=checker_squares,
        pieces=[],
        material_gain=DOUBLE_CHECK_MATERIAL_GAIN,
    )


def detect_hanging_piece(board: chess.Board, color: chess.Color) -> list[TacticalMotif]:
    """Detect undefended pieces that are under attack."""
    enemy_color = not color
    return [
        TacticalMotif(
            pattern=TacticalPattern.HANGING_PIECE,
            description=f"Hanging {chess.piece_name(piece.piece_type)}",
            squares=[sq],
            pieces=[piece.piece_type],
            material_gain=_get_piece_value(piece.piece_type),
        )
        for sq, piece in _iter_friendly_pieces(board, color)
        if piece.piece_type != chess.KING
        and board.is_attacked_by(enemy_color, sq)
        and not board.attackers(color, sq)
    ]


def _iter_friendly_pieces(board: chess.Board, color: chess.Color):
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            yield sq, piece


def _has_king_escape(
    board_after: chess.Board,
    enemy_king_sq: chess.Square,
    enemy_color: chess.Color,
    attacker_color: chess.Color,
) -> bool:
    king_moves = board_after.attacks(enemy_king_sq)
    for sq in chess.SQUARES:
        if not (king_moves & chess.BB_SQUARES[sq]):
            continue
        blocker = board_after.piece_at(sq)
        if blocker and blocker.color == enemy_color:
            continue
        if not board_after.is_attacked_by(attacker_color, sq):
            return True
    return False


def _is_back_rank_mate(
    board_after: chess.Board,
    move: chess.Move,
    enemy_king_sq: chess.Square | None,
    enemy_color: chess.Color,
    attacker_color: chess.Color,
    back_rank: int,
) -> bool:
    if enemy_king_sq is None or not board_after.is_check():
        return False
    if chess.square_rank(enemy_king_sq) != back_rank:
        return False
    if chess.square_rank(move.to_square) != back_rank:
        return False
    return not _has_king_escape(board_after, enemy_king_sq, enemy_color, attacker_color)


def detect_back_rank_threat(
    board: chess.Board, move: chess.Move
) -> TacticalMotif | None:
    """Detect if a move creates a back rank threat."""
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece or moving_piece.piece_type not in (chess.ROOK, chess.QUEEN):
        return None

    board_after = board.copy()
    board_after.push(move)
    enemy_color = not moving_piece.color
    enemy_king_sq = board_after.king(enemy_color)
    back_rank = 7 if enemy_color == chess.BLACK else 0

    if not _is_back_rank_mate(
        board_after, move, enemy_king_sq, enemy_color, moving_piece.color, back_rank
    ):
        return None

    return TacticalMotif(
        pattern=TacticalPattern.BACK_RANK_THREAT,
        description="Back Rank Mate Threat",
        squares=[move.to_square, enemy_king_sq],
        pieces=[chess.KING],
        material_gain=MATE_THREAT_MATERIAL_GAIN,
    )


_MOVE_DETECTORS = (
    detect_fork,
    detect_skewer,
    detect_discovered_attack,
    detect_double_check,
    detect_back_rank_threat,
)


def analyze_move_tactics(board: chess.Board, move: chess.Move) -> TacticalMotif | None:
    """Analyze what tactical pattern a move exploits."""
    tactics: list[TacticalMotif] = []
    for detector in _MOVE_DETECTORS:
        motif = detector(board, move)
        if motif is not None:
            tactics.append(motif)
    if not tactics:
        return None
    return max(tactics, key=lambda t: t.material_gain)


def analyze_position_weaknesses(
    board: chess.Board, color: chess.Color
) -> list[TacticalMotif]:
    """Analyze weaknesses in a position for the given color."""
    return detect_hanging_piece(board, color) + detect_pin(board, color)


def _new_weaknesses(
    before: list[TacticalMotif], after: list[TacticalMotif]
) -> list[TacticalMotif]:
    pre_existing = {(w.pattern, tuple(sorted(w.squares))) for w in before}
    return [
        w for w in after if (w.pattern, tuple(sorted(w.squares))) not in pre_existing
    ]


def classify_blunder_tactics(
    board_before: chess.Board,
    blunder_move: chess.Move,
    best_move: chess.Move | None,
    opponent_reply: chess.Move | None = None,
) -> BlunderTactics:
    """Classify what tactical patterns explain a blunder."""
    result = BlunderTactics()
    reasons: list[str] = []

    if best_move:
        missed = analyze_move_tactics(board_before, best_move)
        if missed:
            result.missed_tactic = missed
            reasons.append(f"Missed {missed.description.lower()}")

    board_after_blunder = board_before.copy()
    board_after_blunder.push(blunder_move)
    player_color = board_before.turn

    _attach_allowed_tactic(
        result, reasons, board_before, board_after_blunder, opponent_reply, player_color
    )

    result.blunder_reason = (
        "; ".join(reasons) if reasons else "Positional error or deep tactical oversight"
    )
    return result


def _attach_allowed_tactic(
    result: BlunderTactics,
    reasons: list[str],
    board_before: chess.Board,
    board_after_blunder: chess.Board,
    opponent_reply: chess.Move | None,
    player_color: chess.Color,
) -> None:
    if opponent_reply:
        allowed = analyze_move_tactics(board_after_blunder, opponent_reply)
        if allowed:
            result.allowed_tactic = allowed
            reasons.append(f"Allowed {allowed.description.lower()}")
        return

    new_weaknesses = _new_weaknesses(
        analyze_position_weaknesses(board_before, player_color),
        analyze_position_weaknesses(board_after_blunder, player_color),
    )
    if new_weaknesses:
        worst = max(new_weaknesses, key=lambda w: w.material_gain)
        result.allowed_tactic = worst
        reasons.append(f"Created {worst.description.lower()}")

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


PATTERN_LABELS = {
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

# Standard piece values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


@dataclass
class TacticalMotif:
    pattern: TacticalPattern
    description: str
    squares: list[chess.Square] = field(default_factory=list)
    pieces: list[chess.PieceType] = field(default_factory=list)
    material_gain: int = 0  # Expected material gain from the tactic


@dataclass
class BlunderTactics:
    """Tactical analysis of a blunder position.

    Attributes:
        missed_tactic: Tactic that the best move would have exploited
        allowed_tactic: Tactic that opponent can now execute after our blunder
        blunder_reason: Human-readable explanation of why this was a blunder
    """

    missed_tactic: TacticalMotif | None = None
    allowed_tactic: TacticalMotif | None = None
    blunder_reason: str = ""

    @property
    def primary_pattern(self) -> TacticalPattern:
        """Return the most significant tactical pattern."""
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
    """Chebyshev distance between two squares."""
    file1, rank1 = chess.square_file(sq1), chess.square_rank(sq1)
    file2, rank2 = chess.square_file(sq2), chess.square_rank(sq2)
    return max(abs(file1 - file2), abs(rank1 - rank2))


def _count_attacked_valuable_pieces(
    board: chess.Board,
    attacker_square: chess.Square,
    attacker_color: chess.Color,
    min_value: int = 0,
) -> list[tuple[chess.Square, chess.PieceType, int]]:
    """Find valuable enemy pieces attacked by a piece on the given square."""
    attacks = board.attacks(attacker_square)
    enemy_color = not attacker_color
    attacked = []

    for sq in chess.SQUARES:
        if attacks & chess.BB_SQUARES[sq]:
            piece = board.piece_at(sq)
            if piece and piece.color == enemy_color:
                value = _get_piece_value(piece.piece_type)
                if value >= min_value:
                    attacked.append((sq, piece.piece_type, value))

    return attacked


def detect_fork(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Detect if a move creates a fork (attacks 2+ valuable pieces)."""
    board_after = board.copy()
    board_after.push(move)

    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None

    attacker_color = moving_piece.color
    attacker_value = _get_piece_value(moving_piece.piece_type)

    attacked = _count_attacked_valuable_pieces(
        board_after, move.to_square, attacker_color
    )

    # Filter to pieces worth at least as much as the attacker (or king)
    valuable_targets = [
        (sq, pt, val)
        for sq, pt, val in attacked
        if val >= attacker_value or pt == chess.KING
    ]

    if len(valuable_targets) >= 2:
        # Calculate material gain (second most valuable piece, since one escapes)
        values = sorted([val for _, _, val in valuable_targets], reverse=True)
        material_gain = values[1] if len(values) > 1 else values[0]

        squares = [move.to_square] + [sq for sq, _, _ in valuable_targets]
        pieces = [pt for _, pt, _ in valuable_targets]

        # Special naming for royal forks
        piece_types = {pt for _, pt, _ in valuable_targets}
        if chess.KING in piece_types and chess.QUEEN in piece_types:
            desc = "Royal Fork (King + Queen)"
        elif chess.KING in piece_types:
            desc = f"Fork with Check ({len(valuable_targets)} pieces)"
        else:
            piece_names = [chess.piece_name(pt) for _, pt, _ in valuable_targets[:2]]
            desc = f"Fork ({' + '.join(piece_names)})"

        return TacticalMotif(
            pattern=TacticalPattern.FORK,
            description=desc,
            squares=squares,
            pieces=pieces,
            material_gain=material_gain,
        )

    return None


def detect_pin(
    board: chess.Board,
    color: chess.Color,
) -> list[TacticalMotif]:
    """Detect all pins against a given color (both absolute and relative)."""
    pins = []
    enemy_color = not color

    # First detect absolute pins (pinned to king) using chess library
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color and board.is_pinned(color, sq):
            pin_mask = board.pin(color, sq)
            pinned_value = _get_piece_value(piece.piece_type)

            # Find the pinning piece
            for pinner_sq in chess.SQUARES:
                if pin_mask & chess.BB_SQUARES[pinner_sq]:
                    pinner = board.piece_at(pinner_sq)
                    if pinner and pinner.color == enemy_color:
                        pins.append(
                            TacticalMotif(
                                pattern=TacticalPattern.PIN,
                                description=f"Absolute Pin ({chess.piece_name(piece.piece_type)} to King)",
                                squares=[sq, pinner_sq],
                                pieces=[piece.piece_type],
                                material_gain=pinned_value,
                            )
                        )
                        break

    # Now detect relative pins (pinned to queen or other valuable pieces)
    for attacker_sq in chess.SQUARES:
        attacker = board.piece_at(attacker_sq)
        if not attacker or attacker.color != enemy_color:
            continue
        if attacker.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue

        attacks = board.attacks(attacker_sq)
        for target_sq in chess.SQUARES:
            if not (attacks & chess.BB_SQUARES[target_sq]):
                continue

            target = board.piece_at(target_sq)
            if not target or target.color != color:
                continue

            ray = chess.ray(attacker_sq, target_sq)
            if not ray:
                continue

            for behind_sq in chess.SQUARES:
                if behind_sq in (attacker_sq, target_sq):
                    continue
                if not (ray & chess.BB_SQUARES[behind_sq]):
                    continue

                if _square_distance(attacker_sq, behind_sq) <= _square_distance(
                    attacker_sq, target_sq
                ):
                    continue

                behind = board.piece_at(behind_sq)
                if not behind or behind.color != color:
                    continue

                if behind.piece_type == chess.KING:
                    continue  # Already handled as absolute pin

                target_value = _get_piece_value(target.piece_type)
                behind_value = _get_piece_value(behind.piece_type)

                if behind_value > target_value:
                    is_duplicate = any(
                        target_sq in p.squares and attacker_sq in p.squares
                        for p in pins
                    )
                    if not is_duplicate:
                        pins.append(
                            TacticalMotif(
                                pattern=TacticalPattern.PIN,
                                description=f"Relative Pin ({chess.piece_name(target.piece_type)} to {chess.piece_name(behind.piece_type)})",
                                squares=[target_sq, attacker_sq, behind_sq],
                                pieces=[target.piece_type, behind.piece_type],
                                material_gain=target_value,
                            )
                        )
                    break

    return pins


def detect_skewer(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Detect if a move creates a skewer."""
    board_after = board.copy()
    board_after.push(move)

    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None

    if moving_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return None

    attacker_color = moving_piece.color
    enemy_color = not attacker_color

    attacks = board_after.attacks(move.to_square)

    for sq in chess.SQUARES:
        if not (attacks & chess.BB_SQUARES[sq]):
            continue

        front_piece = board_after.piece_at(sq)
        if not front_piece or front_piece.color != enemy_color:
            continue

        front_value = _get_piece_value(front_piece.piece_type)

        ray = chess.ray(move.to_square, sq)
        for behind_sq in chess.SQUARES:
            if behind_sq == sq or behind_sq == move.to_square:
                continue
            if not (ray & chess.BB_SQUARES[behind_sq]):
                continue

            if _square_distance(move.to_square, behind_sq) <= _square_distance(
                move.to_square, sq
            ):
                continue

            behind_piece = board_after.piece_at(behind_sq)
            if not behind_piece or behind_piece.color != enemy_color:
                continue

            behind_value = _get_piece_value(behind_piece.piece_type)

            # Skewer: front piece is MORE valuable (must move, exposing piece behind)
            if front_value > behind_value and front_piece.piece_type in (
                chess.KING,
                chess.QUEEN,
                chess.ROOK,
            ):
                return TacticalMotif(
                    pattern=TacticalPattern.SKEWER,
                    description=f"Skewer ({chess.piece_name(front_piece.piece_type)} to {chess.piece_name(behind_piece.piece_type)})",
                    squares=[move.to_square, sq, behind_sq],
                    pieces=[front_piece.piece_type, behind_piece.piece_type],
                    material_gain=behind_value,
                )

    return None


def detect_discovered_attack(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Detect if moving a piece reveals an attack from a piece behind it."""
    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None

    attacker_color = moving_piece.color
    enemy_color = not attacker_color

    board_after = board.copy()
    board_after.push(move)

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.color != attacker_color:
            continue
        if sq == move.to_square:
            continue
        if piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue

        ray = chess.ray(sq, move.from_square)
        if not ray:
            continue

        attacks_before = board.attacks(sq)
        attacks_after = board_after.attacks(sq)
        new_attacks = attacks_after & ~attacks_before

        for target_sq in chess.SQUARES:
            if not (new_attacks & chess.BB_SQUARES[target_sq]):
                continue

            target = board_after.piece_at(target_sq)
            if target and target.color == enemy_color:
                target_value = _get_piece_value(target.piece_type)

                if target.piece_type == chess.KING:
                    return TacticalMotif(
                        pattern=TacticalPattern.DISCOVERED_CHECK,
                        description=f"Discovered Check (by {chess.piece_name(piece.piece_type)})",
                        squares=[sq, move.from_square, target_sq],
                        pieces=[piece.piece_type],
                        material_gain=target_value,
                    )
                elif target_value >= 300:
                    return TacticalMotif(
                        pattern=TacticalPattern.DISCOVERED_ATTACK,
                        description=f"Discovered Attack on {chess.piece_name(target.piece_type)}",
                        squares=[sq, move.from_square, target_sq],
                        pieces=[piece.piece_type, target.piece_type],
                        material_gain=target_value,
                    )

    return None


def detect_double_check(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Detect if a move delivers double check."""
    board_after = board.copy()
    board_after.push(move)

    if not board_after.is_check():
        return None

    checkers = board_after.checkers()
    checker_count = bin(checkers).count("1")

    if checker_count >= 2:
        checker_squares = [
            sq for sq in chess.SQUARES if checkers & chess.BB_SQUARES[sq]
        ]
        return TacticalMotif(
            pattern=TacticalPattern.DOUBLE_CHECK,
            description="Double Check",
            squares=checker_squares,
            pieces=[],
            material_gain=500,  # Double check is very forcing
        )

    return None


def detect_hanging_piece(
    board: chess.Board,
    color: chess.Color,
) -> list[TacticalMotif]:
    """Detect undefended pieces that are under attack."""
    hanging = []
    enemy_color = not color

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.color != color:
            continue
        if piece.piece_type == chess.KING:
            continue

        if not board.is_attacked_by(enemy_color, sq):
            continue

        defenders = board.attackers(color, sq)

        if not defenders:
            value = _get_piece_value(piece.piece_type)
            hanging.append(
                TacticalMotif(
                    pattern=TacticalPattern.HANGING_PIECE,
                    description=f"Hanging {chess.piece_name(piece.piece_type)}",
                    squares=[sq],
                    pieces=[piece.piece_type],
                    material_gain=value,
                )
            )

    return hanging


def detect_back_rank_threat(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Detect if a move creates a back rank threat."""
    board_after = board.copy()
    board_after.push(move)

    moving_piece = board.piece_at(move.from_square)
    if not moving_piece:
        return None

    enemy_color = not moving_piece.color
    enemy_king_sq = board_after.king(enemy_color)
    if enemy_king_sq is None:
        return None

    # Check if king is on back rank
    back_rank = 7 if enemy_color == chess.BLACK else 0
    if chess.square_rank(enemy_king_sq) != back_rank:
        return None

    # Check if our move attacks the back rank
    if moving_piece.piece_type not in (chess.ROOK, chess.QUEEN):
        return None

    # Check if we're attacking the king's rank
    move_rank = chess.square_rank(move.to_square)
    if move_rank != back_rank:
        return None

    # Check if there's a mating threat
    if board_after.is_check():
        # Check if king has escape squares
        king_moves = board_after.attacks(enemy_king_sq)
        has_escape = False
        for sq in chess.SQUARES:
            if not (king_moves & chess.BB_SQUARES[sq]):
                continue
            blocker = board_after.piece_at(sq)
            if blocker and blocker.color == enemy_color:
                continue  # Blocked by own piece
            if not board_after.is_attacked_by(moving_piece.color, sq):
                has_escape = True
                break

        if not has_escape:
            return TacticalMotif(
                pattern=TacticalPattern.BACK_RANK_THREAT,
                description="Back Rank Mate Threat",
                squares=[move.to_square, enemy_king_sq],
                pieces=[chess.KING],
                material_gain=10000,  # Mate threat
            )

    return None


def analyze_move_tactics(
    board: chess.Board,
    move: chess.Move,
) -> TacticalMotif | None:
    """Analyze what tactical pattern a move exploits.

    Returns the most significant tactic created by this move.
    """
    tactics = []

    # Check for fork
    fork = detect_fork(board, move)
    if fork:
        tactics.append(fork)

    # Check for skewer
    skewer = detect_skewer(board, move)
    if skewer:
        tactics.append(skewer)

    # Check for discovered attack/check
    discovered = detect_discovered_attack(board, move)
    if discovered:
        tactics.append(discovered)

    # Check for double check
    double_check = detect_double_check(board, move)
    if double_check:
        tactics.append(double_check)

    # Check for back rank threat
    back_rank = detect_back_rank_threat(board, move)
    if back_rank:
        tactics.append(back_rank)

    if not tactics:
        return None

    # Return the tactic with highest material gain
    return max(tactics, key=lambda t: t.material_gain)


def analyze_position_weaknesses(
    board: chess.Board,
    color: chess.Color,
) -> list[TacticalMotif]:
    """Analyze weaknesses in a position for the given color."""
    weaknesses = []

    # Check for hanging pieces
    hanging = detect_hanging_piece(board, color)
    weaknesses.extend(hanging)

    # Check for pins
    pins = detect_pin(board, color)
    weaknesses.extend(pins)

    return weaknesses


def classify_blunder_tactics(
    board_before: chess.Board,
    blunder_move: chess.Move,
    best_move: chess.Move | None,
    opponent_reply: chess.Move | None = None,
) -> BlunderTactics:
    """Classify what tactical patterns explain a blunder.

    Args:
        board_before: Position before the blunder
        blunder_move: The move that was played (the blunder)
        best_move: The best move according to engine
        opponent_reply: Opponent's best reply after the blunder (if known)

    Returns:
        BlunderTactics with missed and/or allowed tactics identified
    """
    result = BlunderTactics()
    reasons = []

    # 1. Check if best move had a tactic we missed
    if best_move:
        missed = analyze_move_tactics(board_before, best_move)
        if missed:
            result.missed_tactic = missed
            reasons.append(f"Missed {missed.description.lower()}")

    # 2. Check what weaknesses our blunder creates
    board_after_blunder = board_before.copy()
    board_after_blunder.push(blunder_move)

    player_color = board_before.turn

    # Check what new weaknesses exist after our blunder
    weaknesses_after = analyze_position_weaknesses(board_after_blunder, player_color)

    # 3. If we know opponent's reply, check if it's a tactic
    if opponent_reply:
        allowed = analyze_move_tactics(board_after_blunder, opponent_reply)
        if allowed:
            result.allowed_tactic = allowed
            reasons.append(f"Allowed {allowed.description.lower()}")
    elif weaknesses_after:
        # Even without opponent's reply, we can flag hanging pieces we created
        worst_weakness = max(weaknesses_after, key=lambda w: w.material_gain)
        result.allowed_tactic = worst_weakness
        reasons.append(f"Created {worst_weakness.description.lower()}")

    # Build explanation
    if reasons:
        result.blunder_reason = "; ".join(reasons)
    else:
        result.blunder_reason = "Positional error or deep tactical oversight"

    return result


# Legacy compatibility exports
def analyze_blunder_tactics(
    board_before: chess.Board,
    blunder_move: chess.Move,
    best_move: chess.Move | None,
) -> dict:
    """Legacy function for backward compatibility."""
    result = classify_blunder_tactics(board_before, blunder_move, best_move)

    # Convert to old format
    from dataclasses import dataclass, field

    @dataclass
    class TacticsReport:
        patterns: list[TacticalMotif] = field(default_factory=list)
        primary_pattern: TacticalPattern = TacticalPattern.NONE

        @property
        def pattern_ids(self) -> list[int]:
            return [m.pattern.value for m in self.patterns]

        @property
        def pattern_names(self) -> list[str]:
            return [PATTERN_LABELS[m.pattern] for m in self.patterns]

    best_move_report = TacticsReport()
    if result.missed_tactic:
        best_move_report.patterns = [result.missed_tactic]
        best_move_report.primary_pattern = result.missed_tactic.pattern

    blunder_report = TacticsReport()
    if result.allowed_tactic:
        blunder_report.patterns = [result.allowed_tactic]
        blunder_report.primary_pattern = result.allowed_tactic.pattern

    return {
        "position_before": TacticsReport(),
        "blunder_creates": blunder_report,
        "best_move_uses": best_move_report,
    }


# Also export new API
__all__ = [
    "TacticalPattern",
    "TacticalMotif",
    "BlunderTactics",
    "PATTERN_LABELS",
    "classify_blunder_tactics",
    "analyze_move_tactics",
    "analyze_position_weaknesses",
    "detect_fork",
    "detect_pin",
    "detect_skewer",
    "detect_discovered_attack",
    "detect_double_check",
    "detect_hanging_piece",
    "detect_back_rank_threat",
    # Legacy
    "analyze_blunder_tactics",
]

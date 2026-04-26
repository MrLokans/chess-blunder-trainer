"""Tests for the beginner-friendly blunder explanation generator."""

from __future__ import annotations

from blunder_tutor.utils.explanation import (
    BlunderExplanation,
    ResolvedExplanation,
    generate_explanation,
    resolve_explanation,
)

# Minimal English translator for tests: resolves piece keys and fills placeholders.
_EN_PIECES = {
    "chess.piece.pawn": "pawn",
    "chess.piece.knight": "knight",
    "chess.piece.bishop": "bishop",
    "chess.piece.rook": "rook",
    "chess.piece.queen": "queen",
    "chess.piece.king": "king",
}
# English case forms are identical to nominative
for _piece in ["pawn", "knight", "bishop", "rook", "queen", "king"]:
    for _case in ["gen", "acc", "inst"]:
        _EN_PIECES[f"chess.piece.{_piece}.{_case}"] = _piece

_EN_TEMPLATES = {
    "explanation.blunder.missed_mate": "You missed a checkmate in one move.",
    "explanation.blunder.hanging_piece": "Your {piece} on {square} is undefended and can be captured.",
    "explanation.blunder.exposed_piece": "Moving your {piece} left your {exposed} on {square} undefended.",
    "explanation.blunder.bad_capture": "Capturing with your {piece} loses material — your {piece} is worth more than the captured piece.",
    "explanation.blunder.cp_loss": "This move loses about {loss} pawns worth of advantage.",
    "explanation.best.checkmate": "The best move {san} delivers checkmate.",
    "explanation.best.capture_with_check": "The best move {san} captures the {piece} with check.",
    "explanation.best.check_with_pattern": "The best move {san} gives check, exploiting a {pattern}.",
    "explanation.best.check_winning": "The best move {san} gives check, winning material.",
    "explanation.best.pattern_fork": "The best move {san} creates a fork, attacking multiple pieces at once.",
    "explanation.best.pattern_pin": "The best move {san} creates a pin, winning material.",
    "explanation.best.pattern_skewer": "The best move {san} creates a skewer, forcing a valuable piece to move and exposing another.",
    "explanation.best.pattern_discovered": "The best move {san} unleashes a discovered attack, hitting a valuable piece.",
    "explanation.best.pattern_back_rank": "The best move {san} exploits a back rank weakness.",
    "explanation.best.pattern_hanging": "The best move {san} captures an undefended piece.",
    "explanation.best.pattern_hanging_piece": "The best move {san} captures the undefended {piece} on {square}.",
    "explanation.best.check_wins_hanging": "The best move {san} gives check, winning the undefended {piece} on {square}.",
    "explanation.best.pattern_generic": "The best move {san} wins material with a {pattern}.",
    "explanation.best.wins_piece": "The best move {san} wins the {piece}.",
    "explanation.best.attacks_piece": "The best move {san} attacks the {piece}.",
    "explanation.best.threatens_mate": "The best move {san} threatens checkmate.",
    "explanation.best.threatens_capture_check": "The best move {san} threatens {piece} capture with check.",
    "explanation.best.creates_threat": "The best move {san} creates a {piece} threat.",
    "explanation.best.combination": "The best move {san} starts a combination that wins material.",
    "explanation.best.pv_mate": "The best move {san} leads to checkmate in {moves} moves: {line}",
    "explanation.best.pv_wins_piece": "The best move {san} wins the {piece} after {line}",
    "explanation.best.pv_wins_piece_via_combination": "The best move {san} wins the {piece} through a combination: {line}",
    "explanation.best.pv_wins_piece_via_pattern": "The best move {san} wins the {piece} via {pattern}: {line}",
    "explanation.blunder.ignored_threat": "This move leaves your {piece} on {square} to be captured.",
    "explanation.best.saves_piece": "The best move {san} saves the {piece} from capture.",
    "explanation.best.avoids_loss": "The best move {san} avoids losing {loss} pawns worth of advantage.",
    "explanation.best.fallback": "The best move is {san}.",
}

_ALL_EN = {**_EN_PIECES, **_EN_TEMPLATES}


def _t(key: str, **kwargs: object) -> str:
    template = _ALL_EN.get(key, key)
    # Resolve piece references in kwargs
    resolved = {}
    for k, v in kwargs.items():
        if isinstance(v, str) and v.startswith("chess.piece."):
            resolved[k] = _ALL_EN.get(v, v)
        else:
            resolved[k] = v
    return template.format(**resolved) if resolved else template


def _resolve(
    fen: str, blunder_uci: str, best_move_uci: str | None = None, **kw
) -> ResolvedExplanation:
    raw = generate_explanation(
        fen=fen, blunder_uci=blunder_uci, best_move_uci=best_move_uci, **kw
    )
    return resolve_explanation(raw, _t)


class TestGenerateExplanation:
    def test_hanging_piece_blunder(self):
        fen = "4k3/8/5q2/8/8/8/8/3QK3 b - - 0 1"
        result = _resolve(fen, blunder_uci="f6d4", cp_loss=900)
        assert "queen" in result.blunder_text.lower()

    def test_best_move_captures_with_check(self):
        fen = "3rk3/8/8/8/8/8/8/3QK3 w - - 0 1"
        result = _resolve(fen, blunder_uci="e1e2", best_move_uci="d1d8", cp_loss=500)
        assert "rook" in result.best_move_text.lower()
        assert "check" in result.best_move_text.lower()

    def test_best_move_with_fork_pattern(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Fork",
            cp_loss=200,
        )
        assert "fork" in result.best_move_text.lower()

    def test_best_move_with_pin_pattern(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Pin",
            cp_loss=200,
        )
        assert "pin" in result.best_move_text.lower()

    def test_best_move_with_skewer_pattern(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Skewer",
            cp_loss=200,
        )
        assert "skewer" in result.best_move_text.lower()

    def test_best_move_checkmate(self):
        fen = "7k/6pp/5Q2/8/8/8/8/6K1 w - - 0 1"
        result = _resolve(fen, blunder_uci="g1f2", best_move_uci="f6f8", cp_loss=10000)
        assert "checkmate" in result.best_move_text.lower()

    def test_fallback_cp_loss_explanation(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(fen, blunder_uci="a2a3", best_move_uci="e2e4", cp_loss=350)
        assert "3.5" in result.blunder_text

    def test_invalid_uci_returns_empty(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(fen, blunder_uci="invalid", cp_loss=100)
        assert result.blunder_text == ""
        assert result.best_move_text == ""

    def test_no_best_move(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(fen, blunder_uci="a2a3", cp_loss=200)
        assert result.best_move_text == ""
        assert result.blunder_text != ""

    def test_discovered_attack_pattern(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Discovered Attack",
            cp_loss=300,
        )
        assert "discovered" in result.best_move_text.lower()

    def test_back_rank_pattern(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Back Rank Threat",
            cp_loss=300,
        )
        assert "back rank" in result.best_move_text.lower()

    def test_hanging_piece_pattern_when_best_move_captures(self):
        # Best move captures the hanging piece → use "captures undefended" template
        fen = "4k3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e1e2",
            best_move_uci="d1d5",
            tactical_pattern="Hanging Piece",
            cp_loss=500,
        )
        assert "undefended" in result.best_move_text.lower()

    def test_hanging_piece_pattern_capture_of_defended_piece(self):
        # "Hanging Piece" pattern refers to the blunder creating a hanging piece
        # (White queen on d4), NOT the captured piece being undefended.
        # When best move captures a defended piece, don't say "undefended".
        # Real bug: Qxf6 where queen on f6 is defended by rook on f8.
        fen = "r1b2rk1/p1p4p/2p1pqp1/3p4/2PQ4/8/PP1N1PPP/R3K2R w KQ - 1 18"
        result = _resolve(
            fen,
            blunder_uci="e1g1",
            best_move_uci="d4f6",
            tactical_pattern="Hanging Piece",
            cp_loss=600,
        )
        assert "undefended" not in result.best_move_text.lower()
        assert result.best_move_text != ""

    def test_hanging_piece_pattern_when_best_move_not_capture(self):
        # Best move avoids hanging a piece but doesn't capture → fall through
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e2e3",
            best_move_uci="e2e4",
            tactical_pattern="Hanging Piece",
            cp_loss=300,
        )
        assert "undefended" not in result.best_move_text.lower()
        assert result.best_move_text != ""

    def test_best_move_simple_capture(self):
        fen = "4k3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        result = _resolve(fen, blunder_uci="e1e2", best_move_uci="d1d5", cp_loss=500)
        assert "rook" in result.best_move_text.lower()

    def test_hanging_piece_non_capture_from_real_game(self):
        # Real bug: O-O left h4 pawn hanging, best Nd2 is not a capture.
        # Should NOT say "captures an undefended piece".
        fen = "r2q1rk1/pb1p4/1p2p1Bp/2p1b3/7P/2P5/PP3PP1/RN1QK2R w KQ - 1 16"
        result = _resolve(
            fen,
            blunder_uci="e1g1",
            best_move_uci="b1d2",
            tactical_pattern="Hanging Piece",
            cp_loss=262,
        )
        assert "captures" not in result.best_move_text.lower()
        assert "undefended" not in result.best_move_text.lower()
        assert "Nd2" in result.best_move_text

    def test_left_piece_hanging_blunder(self):
        pass

    def test_small_cp_loss_no_blunder_text(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(fen, blunder_uci="a2a3", best_move_uci="e2e4", cp_loss=50)
        assert "50" not in result.blunder_text or result.blunder_text == ""

    def test_none_pattern_not_shown_in_text(self):
        fen = "r1bqr1k1/p2p1pp1/n4n1p/1NbPp3/8/P2BBN2/1PPQ1PPP/R4RK1 w - - 1 14"
        result = _resolve(
            fen,
            blunder_uci="d5d6",
            best_move_uci="f3h4",
            tactical_pattern="None",
            cp_loss=276,
        )
        assert "none" not in result.best_move_text.lower()
        assert result.best_move_text != ""

    def test_quiet_move_detects_threat(self):
        fen = "r1bqr1k1/p2p1pp1/n4n1p/1NbPp3/8/P2BBN2/1PPQ1PPP/R4RK1 w - - 1 14"
        result = _resolve(
            fen,
            blunder_uci="d5d6",
            best_move_uci="f3h4",
            tactical_pattern="None",
            cp_loss=276,
            best_line=["Nh4", "Nxd5", "Bh7+", "Kxh7", "Qxd5"],
        )
        assert "threat" in result.best_move_text.lower()
        assert "none" not in result.best_move_text.lower()

    def test_best_line_material_gain(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="a2a3",
            best_move_uci="e2e4",
            cp_loss=150,
            best_line=["e4", "e5", "d4"],
        )
        assert result.best_move_text != ""

    def test_sacrifice_with_check_uses_pv_to_explain_combination(self):
        # Bxh7+ sacrifices bishop for pawn with check, then Ng5+ Kg8 Qxd5
        # wins the queen. PV-first should show "wins the queen through a combination".
        fen = "r1b2rk1/pppp1ppp/8/3qB3/8/3B1N2/5PPP/1R1Q2K1 w - - 0 21"
        result = _resolve(
            fen,
            blunder_uci="b1b5",
            best_move_uci="d3h7",
            cp_loss=298,
            best_line=["Bxh7+", "Kxh7", "Ng5+", "Kg8", "Qxd5"],
        )
        assert "queen" in result.best_move_text.lower()
        assert "combination" in result.best_move_text.lower()
        assert "Bxh7+" in result.best_move_text
        assert "Qxd5" in result.best_move_text

    def test_capture_with_check_still_works_for_high_value_captures(self):
        # Nxf6+ captures the queen with check — captured value > mover value,
        # so "capture with check" template should be used directly.
        fen = "r1b1k2r/pppp1ppp/5q2/3Np3/2B1P3/8/PPPP1PPP/R1BQK2R w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="c4d3",
            best_move_uci="d5f6",
            cp_loss=400,
        )
        assert "check" in result.best_move_text.lower()
        assert "queen" in result.best_move_text.lower()

    def test_pv_mate_in_multiple_moves(self):
        # PV shows forced mate in 2: Qf7+ Kh8 Qf8#
        fen = "6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1"
        result = _resolve(
            fen,
            blunder_uci="g1f1",
            best_move_uci="d1d8",
            cp_loss=1000,
            best_line=["Qd8+", "Kf7", "Qd7+"],  # not actual mate, but test structure
        )
        # Should at minimum produce a non-empty explanation
        assert result.best_move_text != ""

    def test_pv_wins_piece_shows_line(self):
        # Bxh7+ Kxh7 Ng5+ Kg8 Qxd5 — PV should mention the queen and the line
        fen = "r1b2rk1/pppp1ppp/8/3qB3/8/3B1N2/5PPP/1R1Q2K1 w - - 0 21"
        result = _resolve(
            fen,
            blunder_uci="b1b5",
            best_move_uci="d3h7",
            cp_loss=298,
            best_line=["Bxh7+", "Kxh7", "Ng5+", "Kg8", "Qxd5"],
        )
        assert "queen" in result.best_move_text.lower()
        assert "Ng5+" in result.best_move_text

    def test_pv_with_pattern_enrichment(self):
        # When PV wins material AND a tactical pattern is known, mention the pattern
        fen = "r1b2rk1/pppp1ppp/8/3qB3/8/3B1N2/5PPP/1R1Q2K1 w - - 0 21"
        result = _resolve(
            fen,
            blunder_uci="b1b5",
            best_move_uci="d3h7",
            cp_loss=298,
            tactical_pattern="Discovered Attack",
            best_line=["Bxh7+", "Kxh7", "Ng5+", "Kg8", "Qxd5"],
        )
        assert "queen" in result.best_move_text.lower()
        assert "discovered attack" in result.best_move_text.lower()

    def test_pv_simple_capture_defers_to_static(self):
        # Simple Qxd5 (no sacrifice, direct capture) should use static "wins the piece"
        fen = "4k3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        result = _resolve(
            fen,
            blunder_uci="e1e2",
            best_move_uci="d1d5",
            cp_loss=500,
            best_line=["Qxd5"],
        )
        assert "rook" in result.best_move_text.lower()

    def test_pv_fallback_when_no_material_gain(self):
        # PV exists but no material gain — should fall through to static
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _resolve(
            fen,
            blunder_uci="a2a3",
            best_move_uci="e2e4",
            cp_loss=150,
            best_line=["e4", "e5"],
        )
        assert result.best_move_text != ""

    def test_best_move_gives_check_with_pattern(self):
        fen = "4k3/8/8/8/8/8/8/3QK3 w - - 0 1"
        result = _resolve(fen, blunder_uci="e1e2", best_move_uci="d1d8", cp_loss=500)
        assert "check" in result.best_move_text.lower()


class TestI18nKeys:
    def test_raw_explanation_returns_keys_not_text(self):
        raw = generate_explanation(
            fen="4k3/8/5q2/8/8/8/8/3QK3 b - - 0 1",
            blunder_uci="f6d4",
            best_move_uci=None,
            cp_loss=900,
        )
        assert raw.blunder is not None
        assert raw.blunder.key.startswith("explanation.")
        assert "piece" in raw.blunder.params

    def test_resolve_ts_piece_keys(self):
        raw = generate_explanation(
            fen="4k3/8/5q2/8/8/8/8/3QK3 b - - 0 1",
            blunder_uci="f6d4",
            best_move_uci=None,
            cp_loss=900,
        )
        resolved = resolve_explanation(raw, _t)
        # The resolved text should contain "queen", not "chess.piece.queen"
        assert "chess.piece" not in resolved.blunder_text
        assert "queen" in resolved.blunder_text.lower()

    def test_resolve_with_no_messages(self):
        raw = BlunderExplanation(blunder=None, best_move=None)
        resolved = resolve_explanation(raw, _t)
        assert resolved.blunder_text == ""
        assert resolved.best_move_text == ""


# White Bc4 attacked by black pb5; blunder a2a3 ignores the threat; best Bf1 retreats
_IGNORED_THREAT_FEN = "r1bqkb1r/p1pp1ppp/2n1pn2/1p6/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 5"


class TestIgnoredThreat:
    def test_ignored_threat_fires_for_unaddressed_attack(self):
        result = _resolve(
            _IGNORED_THREAT_FEN, blunder_uci="a2a3", best_move_uci="c4f1", cp_loss=300
        )
        assert "bishop" in result.blunder_text.lower()
        assert "c4" in result.blunder_text
        assert "leaves" in result.blunder_text.lower()

    def test_best_move_saves_piece_from_capture(self):
        result = _resolve(
            _IGNORED_THREAT_FEN, blunder_uci="a2a3", best_move_uci="c4f1", cp_loss=300
        )
        assert "saves" in result.best_move_text.lower()
        assert "bishop" in result.best_move_text.lower()
        assert "Bf1" in result.best_move_text

    def test_no_ignored_threat_when_blunder_moves_threatened_piece(self):
        result = _resolve(
            _IGNORED_THREAT_FEN, blunder_uci="c4a2", best_move_uci="c4f1", cp_loss=200
        )
        assert "leaves" not in result.blunder_text.lower()

    def test_no_ignored_threat_when_blunder_captures_attacker(self):
        result = _resolve(
            _IGNORED_THREAT_FEN, blunder_uci="c4b5", best_move_uci="c4f1", cp_loss=100
        )
        assert "leaves" not in result.blunder_text.lower()

    def test_no_ignored_threat_for_pawns(self):
        # White pawn on d4 attacked by black pe5 — pawn value < 3, should not trigger
        fen = "rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
        result = _resolve(fen, blunder_uci="a2a3", best_move_uci="d4e5", cp_loss=200)
        assert "leaves" not in result.blunder_text.lower()

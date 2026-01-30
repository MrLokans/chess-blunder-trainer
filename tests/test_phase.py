import chess

from blunder_tutor.analysis.phase import classify_phase
from blunder_tutor.constants import PHASE_ENDGAME, PHASE_MIDDLEGAME, PHASE_OPENING


class TestClassifyPhase:
    def test_opening_move_1_full_material(self):
        board = chess.Board()  # Starting position with all 30 pieces (excluding kings)
        assert classify_phase(board, move_number=1) == PHASE_OPENING

    def test_opening_move_10_full_material(self):
        board = chess.Board()
        assert classify_phase(board, move_number=10) == PHASE_OPENING

    def test_opening_move_15_high_material(self):
        board = chess.Board()
        # Starting position has 30 pieces (excluding kings), >= 16 pieces
        assert classify_phase(board, move_number=15) == PHASE_OPENING

    def test_middlegame_move_20_full_material(self):
        board = chess.Board()
        # Move 20 with full material should be middlegame (not opening because move > 15)
        assert classify_phase(board, move_number=20) == PHASE_MIDDLEGAME

    def test_middlegame_typical_position(self):
        # Position with moderate material, middle of the game
        fen = "r1bq1rk1/ppp2ppp/2n2n2/3pp3/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQ - 0 7"
        board = chess.Board(fen)
        # This position has many pieces, move 25 should be middlegame
        assert classify_phase(board, move_number=25) == PHASE_MIDDLEGAME

    def test_endgame_very_few_pieces(self):
        # King + Rook vs King (3 pieces total including kings, so 1 piece excluding kings)
        fen = "8/8/8/4k3/8/8/8/4K2R w - - 0 50"
        board = chess.Board(fen)
        assert classify_phase(board, move_number=50) == PHASE_ENDGAME

    def test_endgame_six_or_fewer_pieces(self):
        # King + Rook + Pawn vs King + Rook (6 pieces excluding kings)
        fen = "8/8/4k3/8/4r3/4P3/8/4K2R w - - 0 40"
        board = chess.Board(fen)
        # 3 pieces excluding kings (R, P, r)
        assert classify_phase(board, move_number=40) == PHASE_ENDGAME

    def test_endgame_late_game_low_material(self):
        # Move 35+ with 10 or fewer pieces should be endgame
        # Position with exactly 8 pieces (excluding kings): 2 rooks + 6 pawns
        fen = "4k3/ppp5/8/8/8/8/PPP5/4K2R w K - 0 35"
        board = chess.Board(fen)
        # R + 6 pawns = 7 pieces excluding kings
        assert classify_phase(board, move_number=35) == PHASE_ENDGAME

    def test_early_trades_leads_to_early_endgame(self):
        # Early game but lots of trades - only 5 pieces, should be endgame regardless of move
        fen = "4k3/8/8/8/8/8/4P3/4K2R w K - 0 15"
        board = chess.Board(fen)
        # R + P = 2 pieces excluding kings (<=6, so endgame)
        result = classify_phase(board, move_number=15)
        assert result == PHASE_ENDGAME

    def test_endgame_threshold_boundary(self):
        # Exactly 6 pieces (excluding kings) should be endgame
        fen = "8/5pk1/8/8/8/8/5PK1/3R1r2 w - - 0 45"
        board = chess.Board(fen)
        # R + r + 2 pawns = 4 pieces excluding kings
        assert classify_phase(board, move_number=45) == PHASE_ENDGAME

    def test_opening_to_middlegame_transition(self):
        board = chess.Board()
        # Move 11 with high material - should be middlegame (not opening, move > 10)
        # But we also check: move <= 15 and pieces >= 16 -> opening
        # Starting position has 30 pieces, so move 11 with 30 pieces should still check the second condition
        # move_number=11 doesn't match first condition (move <= 10)
        # but matches second condition (move <= 15 and pieces >= 16)
        assert classify_phase(board, move_number=11) == PHASE_OPENING
        assert classify_phase(board, move_number=16) == PHASE_MIDDLEGAME

    def test_move_number_affects_classification(self):
        # Same material but different move numbers
        fen = "r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2"
        board = chess.Board(fen)
        # 30 pieces excluding kings
        assert classify_phase(board, move_number=5) == PHASE_OPENING
        assert classify_phase(board, move_number=20) == PHASE_MIDDLEGAME

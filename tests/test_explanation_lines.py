from __future__ import annotations

import chess

from blunder_tutor.analysis.explanation.lines import (
    PVAnalysis,
    analyze_pv,
    final_capture_at_risk,
)


def _line_end(fen: str, moves: list[str]) -> chess.Board:
    board = chess.Board(fen)
    for san in moves:
        board.push_san(san)
    return board


class TestAnalyzePv:
    def test_splits_captures_by_side_and_nets_material(self):
        board = chess.Board("r1b2rk1/pppp1ppp/8/3qB3/8/3B1N2/5PPP/1R1Q2K1 w - - 0 21")
        line = ["Bxh7+", "Kxh7", "Ng5+", "Kg8", "Qxd5"]
        pv = analyze_pv(board, chess.Move.from_uci("d3h7"), line)
        assert pv is not None
        assert pv.player_captures == [chess.PAWN, chess.QUEEN]
        assert pv.opponent_captures == [chess.BISHOP]
        assert pv.balance_gain == 7
        assert not pv.gives_mate

    def test_mate_ends_the_line(self):
        board = chess.Board("5r1k/6pp/8/8/8/8/R7/R5K1 w - - 0 1")
        pv = analyze_pv(board, chess.Move.from_uci("a2a8"), ["Ra8", "Rxa8", "Rxa8#"])
        assert pv is not None
        assert pv.gives_mate

    def test_unparsable_quiet_line_is_unusable(self):
        # The second move is illegal, and the first neither captures nor checks.
        board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
        assert analyze_pv(board, chess.Move.from_uci("a1a2"), ["Ra2", "Qh5"]) is None


class TestFinalCaptureAtRisk:
    def test_undefended_capturer_is_assumed_lost(self):
        # Rxd8+ ends the line; the c8 rook takes back.
        board = _line_end(
            "2rr2k1/p4ppp/8/8/8/4B3/5PPP/3R2K1 w - - 0 1", ["Bxa7", "h6", "Rxd8+"]
        )
        assert final_capture_at_risk(board, chess.WHITE) == chess.ROOK

    def test_capture_the_king_cannot_take_back_is_kept(self):
        # Rhxh2: the king can't take a rook guarded by the f2 rook.
        board = _line_end(
            "6r1/ppk2p1p/2p5/4R3/N7/2P5/PP3r1P/1R5K b - - 0 31",
            ["Rg4", "b3", "Rh4", "Kg1", "Rhxh2"],
        )
        assert final_capture_at_risk(board, chess.BLACK) is None

    def test_opponent_move_last_is_never_at_risk(self):
        board = _line_end("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", ["Ra8+", "Kd7"])
        assert final_capture_at_risk(board, chess.WHITE) is None


def _pv(
    gain: int, won: list[int], lost: list[int], at_risk: int | None = None
) -> PVAnalysis:
    return PVAnalysis(
        moves_san=[],
        gives_mate=False,
        balance_gain=gain,
        player_captures=won,
        opponent_captures=lost,
        assumed_recapture=at_risk,
    )


class TestNetPieceWon:
    def test_like_for_like_trade_cancels(self):
        # Queens traded, knight won: name the knight.
        pv = _pv(3, [chess.KNIGHT, chess.QUEEN], [chess.QUEEN])
        assert pv.net_piece_won == chess.KNIGHT

    def test_assumed_recapture_cancels_too(self):
        pv = _pv(1, [chess.PAWN, chess.ROOK], [], at_risk=chess.ROOK)
        assert pv.net_piece_won == chess.PAWN

    def test_big_give_back_names_nothing(self):
        # A queen for a rook and two pawns: too much given back to call it a won queen.
        pv = _pv(2, [chess.QUEEN], [chess.ROOK, chess.PAWN, chess.PAWN])
        assert pv.net_piece_won is None

    def test_no_gain_names_nothing(self):
        assert _pv(0, [chess.KNIGHT], [chess.BISHOP]).net_piece_won is None

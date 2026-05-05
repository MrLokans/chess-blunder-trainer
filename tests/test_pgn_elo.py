from __future__ import annotations

from blunder_tutor.utils.pgn_headers import extract_player_elos


class TestExtractPlayerElos:
    def test_both_elos_present(self) -> None:
        pgn = '[White "A"]\n[Black "B"]\n[WhiteElo "1500"]\n[BlackElo "1480"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white == 1500
        assert black == 1480

    def test_only_white_present(self) -> None:
        pgn = '[White "A"]\n[Black "B"]\n[WhiteElo "1500"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white == 1500
        assert black is None

    def test_only_black_present(self) -> None:
        pgn = '[White "A"]\n[Black "B"]\n[BlackElo "1480"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white is None
        assert black == 1480

    def test_both_missing(self) -> None:
        pgn = '[White "A"]\n[Black "B"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white is None
        assert black is None

    def test_question_mark_placeholder(self) -> None:
        pgn = '[WhiteElo "?"]\n[BlackElo "?"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white is None
        assert black is None

    def test_empty_string_value(self) -> None:
        pgn = '[WhiteElo ""]\n[BlackElo ""]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white is None
        assert black is None

    def test_non_numeric_junk(self) -> None:
        pgn = '[WhiteElo "abc"]\n[BlackElo "1500"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white is None
        assert black == 1500

    def test_provisional_question_mark_suffix(self) -> None:
        # Some PGNs annotate provisional ratings as "1500?". Treat as int 1500.
        pgn = '[WhiteElo "1500?"]\n[BlackElo "1500"]\n\n*\n'
        white, black = extract_player_elos(pgn)
        assert white == 1500
        assert black == 1500

    def test_does_not_match_inside_move_text(self) -> None:
        # Defensive: make sure we don't match a fake header from the move comments.
        pgn = (
            '[White "A"]\n[Black "B"]\n[WhiteElo "1500"]\n[BlackElo "1480"]\n\n'
            '1. e4 { fake [WhiteElo "9999"] in comment } e5 *\n'
        )
        white, black = extract_player_elos(pgn)
        # First match wins for the real header at the top.
        assert white == 1500
        assert black == 1480

from __future__ import annotations

import tempfile
from pathlib import Path

import chess.pgn
import pytest

from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    extract_game_url,
    load_game,
    load_game_from_string,
    normalize_pgn,
)


class TestLoadGame:
    def test_load_valid_game(self):
        pgn_content = """[Event "Test Game"]
[Site "Test"]
[Date "2023.12.25"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pgn", delete=False, encoding="utf-8"
        ) as f:
            f.write(pgn_content)
            temp_path = Path(f.name)

        try:
            game = load_game(temp_path)
            assert isinstance(game, chess.pgn.Game)
            assert game.headers["Event"] == "Test Game"
            assert game.headers["White"] == "Player1"
            assert game.headers["Black"] == "Player2"
            assert game.headers["Result"] == "1-0"
        finally:
            temp_path.unlink()

    def test_load_game_with_moves(self):
        pgn_content = """[Event "Test"]
[Site "Test"]
[Date "2023.12.25"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "*"]

1. e4 e5 2. Nf3 *
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pgn", delete=False, encoding="utf-8"
        ) as f:
            f.write(pgn_content)
            temp_path = Path(f.name)

        try:
            game = load_game(temp_path)
            moves = list(game.mainline_moves())
            assert len(moves) == 3
            assert moves[0].uci() == "e2e4"
            assert moves[1].uci() == "e7e5"
            assert moves[2].uci() == "g1f3"
        finally:
            temp_path.unlink()

    def test_load_empty_pgn(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pgn", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid PGN"):
                load_game(temp_path)
        finally:
            temp_path.unlink()

    def test_load_invalid_pgn(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pgn", delete=False, encoding="utf-8"
        ) as f:
            f.write("This is not a valid PGN file at all\n")
            f.write("No headers, no moves\n")
            temp_path = Path(f.name)

        try:
            result = load_game(temp_path)
            assert result is not None
        except ValueError:
            pass
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        nonexistent = Path("/tmp/nonexistent_game_12345.pgn")
        with pytest.raises(FileNotFoundError):
            load_game(nonexistent)


class TestLoadGameFromString:
    def test_load_valid_game(self):
        pgn_content = """[Event "Test Game"]
[Site "Test"]
[Date "2023.12.25"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""
        game = load_game_from_string(pgn_content)
        assert isinstance(game, chess.pgn.Game)
        assert game.headers["Event"] == "Test Game"
        assert game.headers["White"] == "Player1"

    def test_load_empty_string(self):
        with pytest.raises(ValueError, match="Invalid PGN content"):
            load_game_from_string("")

    def test_load_game_moves(self):
        pgn_content = """[Event "Test"]
[White "Player1"]
[Black "Player2"]
[Result "*"]

1. e4 e5 2. Nf3 *
"""
        game = load_game_from_string(pgn_content)
        moves = list(game.mainline_moves())
        assert len(moves) == 3


class TestNormalizePgn:
    def test_normalizes_line_endings(self):
        pgn_crlf = '[Event "Test"]\r\n[White "Player1"]\r\n'
        pgn_lf = '[Event "Test"]\n[White "Player1"]\n'

        assert normalize_pgn(pgn_crlf) == normalize_pgn(pgn_lf)

    def test_strips_whitespace(self):
        pgn = '  [Event "Test"]\n  '
        normalized = normalize_pgn(pgn)
        assert normalized.startswith("[Event")
        assert normalized.endswith("\n")

    def test_ensures_trailing_newline(self):
        pgn = '[Event "Test"]'
        normalized = normalize_pgn(pgn)
        assert normalized.endswith("\n")


class TestComputeGameId:
    def test_returns_sha256_hex(self):
        pgn = '[Event "Test"]\n'
        game_id = compute_game_id(pgn)
        assert len(game_id) == 64
        assert all(c in "0123456789abcdef" for c in game_id)

    def test_same_content_same_id(self):
        pgn = '[Event "Test"]\n'
        assert compute_game_id(pgn) == compute_game_id(pgn)

    def test_different_content_different_id(self):
        pgn1 = '[Event "Test1"]\n'
        pgn2 = '[Event "Test2"]\n'
        assert compute_game_id(pgn1) != compute_game_id(pgn2)


class TestExtractGameUrl:
    def test_lichess_site_header(self):
        game = load_game_from_string(
            '[Site "https://lichess.org/3bsmejYN"]\n[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'
        )
        assert extract_game_url(game) == "https://lichess.org/3bsmejYN"

    def test_chesscom_link_header(self):
        game = load_game_from_string(
            '[Site "Chess.com"]\n[Link "https://www.chess.com/game/live/123"]\n'
            '[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'
        )
        assert extract_game_url(game) == "https://www.chess.com/game/live/123"

    def test_chesscom_link_takes_priority_over_non_url_site(self):
        game = load_game_from_string(
            '[Site "Chess.com"]\n[Link "https://www.chess.com/game/live/456"]\n'
            '[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'
        )
        assert extract_game_url(game) == "https://www.chess.com/game/live/456"

    def test_no_url_headers(self):
        game = load_game_from_string(
            '[Site "Local Club"]\n[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'
        )
        assert extract_game_url(game) is None

    def test_missing_both_headers(self):
        game = load_game_from_string('[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n')
        assert extract_game_url(game) is None


class TestBuildGameMetadata:
    def test_build_metadata_basic(self):
        pgn_text = """[Event "Test Tournament"]
[Site "Test City"]
[Date "2023.12.25"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]
[UTCDate "2023.12.25"]
[UTCTime "14:30:00"]

1. e4 e5 1-0
"""
        metadata = build_game_metadata(pgn_text, "lichess", "Player1")
        assert metadata["source"] == "lichess"
        assert metadata["username"] == "Player1"
        assert metadata["white"] == "Player1"
        assert metadata["black"] == "Player2"
        assert metadata["result"] == "1-0"
        assert metadata["end_time_utc"] is not None
        assert "id" in metadata
        assert "pgn_content" in metadata

    def test_build_metadata_empty(self):
        metadata = build_game_metadata("", "lichess", "test")
        assert metadata == {}

    def test_build_metadata_minimal(self):
        pgn_text = """[White "Player1"]
[Black "Player2"]
[Result "*"]

*
"""
        metadata = build_game_metadata(pgn_text, "chesscom", "Player1")
        assert metadata["white"] == "Player1"
        assert metadata["black"] == "Player2"
        assert metadata["source"] == "chesscom"
        assert metadata["username"] == "Player1"

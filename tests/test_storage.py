from __future__ import annotations

import tempfile
from pathlib import Path

from blunder_tutor.storage import store_pgn


class TestStorePgn:
    def test_store_new_game(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            pgn_text = """[Event "Test"]
[Site "Test"]
[Date "2023.12.25"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 1-0
"""
            result = store_pgn("test", "testuser", pgn_text, data_dir)

            assert result is not None
            path, metadata = result
            assert path.exists()
            assert "test" in str(path)
            assert "testuser" in str(path)

            # Verify content
            content = path.read_text()
            assert "Player1" in content
            assert "Player2" in content

            # Verify metadata
            assert metadata["source"] == "test"
            assert metadata["username"] == "testuser"
            assert metadata["white"] == "Player1"
            assert metadata["black"] == "Player2"

    def test_store_duplicate_game(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            pgn_text = """[Event "Test"]
[Site "Test"]
[Date "2023.12.25"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 1-0
"""
            # Store first time
            result1 = store_pgn("test", "testuser", pgn_text, data_dir)
            assert result1 is not None

            # Store again (duplicate)
            result2 = store_pgn("test", "testuser", pgn_text, data_dir)
            assert result2 is None

    def test_store_normalizes_pgn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            # Two PGNs with different line endings should be considered the same
            pgn1 = '[Event "Test"]\n[White "Player1"]\n[Black "Player2"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n'
            pgn2 = '[Event "Test"]\r\n[White "Player1"]\r\n[Black "Player2"]\r\n[Result "1-0"]\r\n\r\n1. e4 e5 1-0\r\n'

            result1 = store_pgn("test", "testuser", pgn1, data_dir)
            result2 = store_pgn("test", "testuser", pgn2, data_dir)

            # Both should produce the same hash (normalized line endings)
            assert result1 is not None
            assert result2 is None  # Duplicate

    def test_store_creates_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            pgn_text = """[Event "Test"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 1-0
"""
            result = store_pgn("test", "testuser", pgn_text, data_dir)

            assert result is not None
            path, _metadata = result
            assert path.parent.exists()
            assert path.parent.name == "testuser"
            assert path.parent.parent.name == "test"

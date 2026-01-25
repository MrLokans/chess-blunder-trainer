from __future__ import annotations

import json
import tempfile
from pathlib import Path

from blunder_tutor.index import append_index, build_metadata, read_index


class TestBuildMetadata:
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
        metadata = build_metadata(pgn_text)
        assert metadata["event"] == "Test Tournament"
        assert metadata["site"] == "Test City"
        assert metadata["white"] == "Player1"
        assert metadata["black"] == "Player2"
        assert metadata["result"] == "1-0"
        assert metadata["end_time_utc"] is not None

    def test_build_metadata_empty(self):
        metadata = build_metadata("")
        assert metadata == {}

    def test_build_metadata_minimal(self):
        pgn_text = """[White "Player1"]
[Black "Player2"]
[Result "*"]

*
"""
        metadata = build_metadata(pgn_text)
        assert metadata["white"] == "Player1"
        assert metadata["black"] == "Player2"


class TestAppendIndex:
    def test_append_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            record = {
                "id": "test123",
                "source": "test",
                "username": "testuser",
                "white": "Player1",
                "black": "Player2",
            }

            append_index(data_dir, record)

            index_path = data_dir / "index" / "games.jsonl"
            assert index_path.exists()

            with index_path.open("r") as f:
                lines = f.readlines()
                assert len(lines) == 1
                saved_record = json.loads(lines[0])
                assert saved_record["id"] == "test123"
                assert saved_record["username"] == "testuser"

    def test_append_multiple_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            for i in range(3):
                record = {
                    "id": f"test{i}",
                    "source": "test",
                    "username": "testuser",
                }
                append_index(data_dir, record)

            index_path = data_dir / "index" / "games.jsonl"
            with index_path.open("r") as f:
                lines = f.readlines()
                assert len(lines) == 3


class TestReadIndex:
    """Tests for read_index function."""

    def test_read_index_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            records = list(read_index(data_dir))
            assert records == []

    def test_read_index_with_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            # Add some records
            records_to_add = [
                {"id": "game1", "source": "lichess", "username": "user1"},
                {"id": "game2", "source": "chesscom", "username": "user2"},
                {"id": "game3", "source": "lichess", "username": "user1"},
            ]

            for record in records_to_add:
                append_index(data_dir, record)

            # Read all records
            records = list(read_index(data_dir))
            assert len(records) == 3

    def test_read_index_filter_by_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            records_to_add = [
                {"id": "game1", "source": "lichess", "username": "user1"},
                {"id": "game2", "source": "chesscom", "username": "user2"},
                {"id": "game3", "source": "lichess", "username": "user1"},
            ]

            for record in records_to_add:
                append_index(data_dir, record)

            # Filter by source
            lichess_records = list(read_index(data_dir, source="lichess"))
            assert len(lichess_records) == 2
            assert all(r["source"] == "lichess" for r in lichess_records)

    def test_read_index_filter_by_username(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            records_to_add = [
                {"id": "game1", "source": "lichess", "username": "user1"},
                {"id": "game2", "source": "chesscom", "username": "user2"},
                {"id": "game3", "source": "lichess", "username": "user1"},
            ]

            for record in records_to_add:
                append_index(data_dir, record)

            # Filter by username
            user1_records = list(read_index(data_dir, username="user1"))
            assert len(user1_records) == 2
            assert all(r["username"] == "user1" for r in user1_records)

    def test_read_index_filter_both(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)

            records_to_add = [
                {"id": "game1", "source": "lichess", "username": "user1"},
                {"id": "game2", "source": "chesscom", "username": "user1"},
                {"id": "game3", "source": "lichess", "username": "user2"},
            ]

            for record in records_to_add:
                append_index(data_dir, record)

            # Filter by both
            filtered = list(read_index(data_dir, source="lichess", username="user1"))
            assert len(filtered) == 1
            assert filtered[0]["id"] == "game1"

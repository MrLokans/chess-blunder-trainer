"""Tests for time control parsing and game type classification."""

import pytest

from blunder_tutor.utils.time_control import (
    GameType,
    classify_game_type,
    estimate_game_duration,
    get_game_type_from_label,
    get_game_type_label,
    parse_time_control,
)


class TestParseTimeControl:
    def test_parse_standard_format(self):
        assert parse_time_control("180+0") == (180, 0)
        assert parse_time_control("600+5") == (600, 5)
        assert parse_time_control("900+10") == (900, 10)

    def test_parse_bullet(self):
        assert parse_time_control("60+0") == (60, 0)
        assert parse_time_control("120+1") == (120, 1)

    def test_parse_chesscom_format(self):
        # Chess.com often uses just seconds without increment
        assert parse_time_control("600") == (600, 0)
        assert parse_time_control("180") == (180, 0)
        assert parse_time_control("60") == (60, 0)
        assert parse_time_control("300") == (300, 0)

    def test_parse_none(self):
        assert parse_time_control(None) is None
        assert parse_time_control("") is None

    def test_parse_invalid_format(self):
        assert parse_time_control("invalid") is None
        assert parse_time_control("1/86400") is None  # Correspondence format
        assert parse_time_control("-") is None  # Daily game marker


class TestEstimateGameDuration:
    def test_no_increment(self):
        assert estimate_game_duration(180, 0) == 180  # 3 min
        assert estimate_game_duration(600, 0) == 600  # 10 min

    def test_with_increment(self):
        # 3 + 40 * 2 = 83 seconds per side => 166 total, we compute per side
        assert estimate_game_duration(180, 2) == 180 + 40 * 2  # 260
        assert estimate_game_duration(600, 5) == 600 + 40 * 5  # 800


class TestClassifyGameType:
    def test_ultrabullet(self):
        # < 29 seconds
        assert classify_game_type("15+0") == GameType.ULTRABULLET
        assert classify_game_type("20+0") == GameType.ULTRABULLET
        assert classify_game_type("15") == GameType.ULTRABULLET  # Chess.com format

    def test_bullet(self):
        # >= 29s and < 180s
        assert classify_game_type("60+0") == GameType.BULLET
        assert classify_game_type("120+0") == GameType.BULLET
        assert classify_game_type("60+1") == GameType.BULLET  # 60 + 40 = 100
        # Chess.com format (no increment)
        assert classify_game_type("60") == GameType.BULLET
        assert classify_game_type("120") == GameType.BULLET

    def test_blitz(self):
        # >= 180s and < 480s
        assert classify_game_type("180+0") == GameType.BLITZ
        assert classify_game_type("300+0") == GameType.BLITZ
        assert classify_game_type("180+2") == GameType.BLITZ  # 180 + 80 = 260
        # Chess.com format (no increment)
        assert classify_game_type("180") == GameType.BLITZ
        assert classify_game_type("300") == GameType.BLITZ

    def test_rapid(self):
        # >= 480s and < 1500s
        assert classify_game_type("600+0") == GameType.RAPID
        assert classify_game_type("900+0") == GameType.RAPID
        assert classify_game_type("600+5") == GameType.RAPID  # 600 + 200 = 800
        assert classify_game_type("900+10") == GameType.RAPID  # 900 + 400 = 1300
        # Chess.com format (no increment)
        assert classify_game_type("600") == GameType.RAPID
        assert classify_game_type("900") == GameType.RAPID

    def test_classical(self):
        # >= 1500s
        assert classify_game_type("1800+0") == GameType.CLASSICAL
        assert classify_game_type("1800+30") == GameType.CLASSICAL
        assert classify_game_type("900+15") == GameType.CLASSICAL  # 900 + 600 = 1500
        # Chess.com format (no increment)
        assert classify_game_type("1800") == GameType.CLASSICAL

    def test_correspondence(self):
        assert classify_game_type("1/86400") == GameType.CORRESPONDENCE
        # Chess.com uses "-" for daily games
        assert classify_game_type("-") == GameType.CORRESPONDENCE

    def test_unknown(self):
        assert classify_game_type(None) == GameType.UNKNOWN
        assert classify_game_type("") == GameType.UNKNOWN
        assert classify_game_type("invalid") == GameType.UNKNOWN


class TestGameTypeLabels:
    def test_get_label(self):
        assert get_game_type_label(GameType.BULLET) == "bullet"
        assert get_game_type_label(GameType.BLITZ) == "blitz"
        assert get_game_type_label(GameType.RAPID) == "rapid"
        assert get_game_type_label(GameType.CLASSICAL) == "classical"

    def test_get_from_label(self):
        assert get_game_type_from_label("bullet") == GameType.BULLET
        assert get_game_type_from_label("blitz") == GameType.BLITZ
        assert get_game_type_from_label("RAPID") == GameType.RAPID
        assert get_game_type_from_label("unknown_value") == GameType.UNKNOWN


class TestGameTypeValues:
    def test_game_type_int_values(self):
        assert int(GameType.ULTRABULLET) == 0
        assert int(GameType.BULLET) == 1
        assert int(GameType.BLITZ) == 2
        assert int(GameType.RAPID) == 3
        assert int(GameType.CLASSICAL) == 4
        assert int(GameType.CORRESPONDENCE) == 5
        assert int(GameType.UNKNOWN) == 6

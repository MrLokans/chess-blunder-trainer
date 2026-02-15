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
    @pytest.mark.parametrize(
        "tc,expected",
        [
            ("180+0", (180, 0)),
            ("600+5", (600, 5)),
            ("900+10", (900, 10)),
            ("60+0", (60, 0)),
            ("120+1", (120, 1)),
            ("600", (600, 0)),
            ("180", (180, 0)),
            ("60", (60, 0)),
            ("300", (300, 0)),
        ],
    )
    def test_valid_formats(self, tc, expected):
        assert parse_time_control(tc) == expected

    @pytest.mark.parametrize("tc", [None, "", "invalid", "1/86400", "-"])
    def test_invalid_formats(self, tc):
        assert parse_time_control(tc) is None


class TestEstimateGameDuration:
    @pytest.mark.parametrize(
        "base,inc,expected",
        [
            (180, 0, 180),
            (600, 0, 600),
            (180, 2, 260),
            (600, 5, 800),
        ],
    )
    def test_duration(self, base, inc, expected):
        assert estimate_game_duration(base, inc) == expected


class TestClassifyGameType:
    @pytest.mark.parametrize(
        "tc,expected",
        [
            ("15+0", GameType.ULTRABULLET),
            ("20+0", GameType.ULTRABULLET),
            ("15", GameType.ULTRABULLET),
            ("60+0", GameType.BULLET),
            ("120+0", GameType.BULLET),
            ("60+1", GameType.BULLET),
            ("60", GameType.BULLET),
            ("120", GameType.BULLET),
            ("180+0", GameType.BLITZ),
            ("300+0", GameType.BLITZ),
            ("180+2", GameType.BLITZ),
            ("180", GameType.BLITZ),
            ("300", GameType.BLITZ),
            ("600+0", GameType.RAPID),
            ("900+0", GameType.RAPID),
            ("600+5", GameType.RAPID),
            ("900+10", GameType.RAPID),
            ("600", GameType.RAPID),
            ("900", GameType.RAPID),
            ("1800+0", GameType.CLASSICAL),
            ("1800+30", GameType.CLASSICAL),
            ("900+15", GameType.CLASSICAL),
            ("1800", GameType.CLASSICAL),
            ("1/86400", GameType.CORRESPONDENCE),
            ("-", GameType.CORRESPONDENCE),
        ],
    )
    def test_classification(self, tc, expected):
        assert classify_game_type(tc) == expected

    @pytest.mark.parametrize("tc", [None, "", "invalid"])
    def test_unknown(self, tc):
        assert classify_game_type(tc) == GameType.UNKNOWN


class TestGameTypeLabels:
    @pytest.mark.parametrize(
        "game_type,label",
        [
            (GameType.BULLET, "bullet"),
            (GameType.BLITZ, "blitz"),
            (GameType.RAPID, "rapid"),
            (GameType.CLASSICAL, "classical"),
        ],
    )
    def test_get_label(self, game_type, label):
        assert get_game_type_label(game_type) == label

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("bullet", GameType.BULLET),
            ("blitz", GameType.BLITZ),
            ("RAPID", GameType.RAPID),
            ("unknown_value", GameType.UNKNOWN),
        ],
    )
    def test_get_from_label(self, label, expected):
        assert get_game_type_from_label(label) == expected


class TestGameTypeValues:
    @pytest.mark.parametrize(
        "game_type,value",
        [
            (GameType.ULTRABULLET, 0),
            (GameType.BULLET, 1),
            (GameType.BLITZ, 2),
            (GameType.RAPID, 3),
            (GameType.CLASSICAL, 4),
            (GameType.CORRESPONDENCE, 5),
            (GameType.UNKNOWN, 6),
        ],
    )
    def test_int_value(self, game_type, value):
        assert int(game_type) == value

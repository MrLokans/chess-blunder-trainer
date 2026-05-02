from __future__ import annotations

import json
from pathlib import Path

import pytest

from blunder_tutor.fetchers._modes import (
    CANONICAL_MODES,
    chesscom_to_canonical,
    lichess_to_canonical,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def lichess_payload() -> dict[str, object]:
    return json.loads((FIXTURES_DIR / "lichess_user_response.json").read_text())


@pytest.fixture
def chesscom_payload() -> dict[str, object]:
    return json.loads((FIXTURES_DIR / "chesscom_player_stats.json").read_text())


class TestLichessToCanonical:
    def test_returns_only_canonical_modes(
        self, lichess_payload: dict[str, object]
    ) -> None:
        snapshots = lichess_to_canonical(lichess_payload["perfs"])
        modes = {snap.mode for snap in snapshots}
        assert modes == set(CANONICAL_MODES)

    def test_drops_puzzle_and_variants(
        self, lichess_payload: dict[str, object]
    ) -> None:
        snapshots = lichess_to_canonical(lichess_payload["perfs"])
        modes = {snap.mode for snap in snapshots}
        for dropped in ("puzzle", "racingKings", "atomic", "ultraBullet"):
            assert dropped not in modes

    def test_carries_rating_and_games_count(
        self, lichess_payload: dict[str, object]
    ) -> None:
        snapshots = lichess_to_canonical(lichess_payload["perfs"])
        bullet = next(s for s in snapshots if s.mode == "bullet")
        assert bullet.rating == 2400
        assert bullet.games_count == 1200

    def test_empty_perfs_yields_empty_list(self) -> None:
        assert not lichess_to_canonical({})

    def test_skips_mode_with_non_dict_block(self) -> None:
        snapshots = lichess_to_canonical(
            {"bullet": "broken", "blitz": {"games": 5, "rating": 1500}}
        )
        modes = {snap.mode for snap in snapshots}
        assert modes == {"blitz"}

    def test_missing_rating_becomes_none(self) -> None:
        snapshots = lichess_to_canonical({"bullet": {"games": 10}})
        bullet = next(s for s in snapshots if s.mode == "bullet")
        assert bullet.rating is None
        assert bullet.games_count == 10


class TestChesscomToCanonical:
    def test_returns_canonical_modes_only(
        self, chesscom_payload: dict[str, object]
    ) -> None:
        snapshots = chesscom_to_canonical(chesscom_payload)
        modes = {snap.mode for snap in snapshots}
        # Chess.com doesn't have classical, so the canonical set we emit is 4.
        assert modes == {"bullet", "blitz", "rapid", "correspondence"}

    def test_daily_maps_to_correspondence(
        self, chesscom_payload: dict[str, object]
    ) -> None:
        snapshots = chesscom_to_canonical(chesscom_payload)
        correspondence = next(s for s in snapshots if s.mode == "correspondence")
        # last.rating from chess_daily.
        assert correspondence.rating == 2050

    def test_games_count_sums_win_loss_draw(
        self, chesscom_payload: dict[str, object]
    ) -> None:
        snapshots = chesscom_to_canonical(chesscom_payload)
        bullet = next(s for s in snapshots if s.mode == "bullet")
        # win=1500, loss=1300, draw=200 → 3000.
        assert bullet.games_count == 3000

    def test_drops_non_canonical_blocks(
        self, chesscom_payload: dict[str, object]
    ) -> None:
        snapshots = chesscom_to_canonical(chesscom_payload)
        modes = {snap.mode for snap in snapshots}
        for dropped in ("tactics", "lessons", "puzzle_rush", "chess960_daily"):
            assert dropped not in modes

    def test_empty_payload_yields_empty_list(self) -> None:
        assert not chesscom_to_canonical({})

    def test_handles_missing_record_or_last(self) -> None:
        snapshots = chesscom_to_canonical({"chess_bullet": {"last": {"rating": 1500}}})
        bullet = next(s for s in snapshots if s.mode == "bullet")
        assert bullet.rating == 1500
        assert bullet.games_count == 0


class TestEmptyBlockSymmetry:
    """Both providers emit a snapshot for an empty-but-present inner block.

    Pins the consistency invariant: a stub block (e.g. `{"chess_daily": {}}`
    from Chess.com) produces a `(rating=None, games_count=0)` snapshot, just
    like an empty `{"bullet": {}}` from Lichess. Skipping happens only when
    the block is missing entirely or is not a dict.
    """

    def test_lichess_empty_block_emits_zero_snapshot(self) -> None:
        snapshots = lichess_to_canonical({"bullet": {}})
        modes = {snap.mode for snap in snapshots}
        assert modes == {"bullet"}
        bullet = snapshots[0]
        assert bullet.rating is None
        assert bullet.games_count == 0

    def test_chesscom_empty_block_emits_zero_snapshot(self) -> None:
        snapshots = chesscom_to_canonical({"chess_bullet": {}})
        modes = {snap.mode for snap in snapshots}
        assert modes == {"bullet"}
        bullet = snapshots[0]
        assert bullet.rating is None
        assert bullet.games_count == 0

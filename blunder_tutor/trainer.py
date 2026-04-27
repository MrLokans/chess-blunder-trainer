from __future__ import annotations

import contextlib
import random
from dataclasses import dataclass

import chess

from blunder_tutor.analysis.filtering import filter_blunders
from blunder_tutor.analysis.tactics import classify_blunder_tactics
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository
from blunder_tutor.utils.pgn_utils import (
    board_before_ply,
    extract_game_url,
    move_uci_at_ply,
)

# Puzzle-weighting heuristics. These multipliers tune how the trainer
# samples blunders: short mate misses are the most learnable, easy-but-
# missed blunders are higher signal than tough engine-line tactics, and
# unseen patterns get a small exploration bonus.
_WEIGHT_MATE_VERY_SHORT = 2.0  # mate-in ≤ 2
_WEIGHT_MATE_SHORT = 1.5  # mate-in ≤ 5
_MATE_DEPTH_VERY_SHORT = 2
_MATE_DEPTH_SHORT = 5

_WEIGHT_UNSEEN_PATTERN = 1.5

_WEIGHT_EASY_DIFFICULTY = 1.3  # difficulty ≤ 30
_WEIGHT_HARD_DIFFICULTY = 0.7  # difficulty ≥ 70
_DIFFICULTY_EASY = 30
_DIFFICULTY_HARD = 70

_DEFAULT_SPACED_REPETITION_DAYS = 30


@dataclass(frozen=True)
class BlunderFilter:
    start_date: str | None = None
    end_date: str | None = None
    exclude_recently_solved: bool = True
    spaced_repetition_days: int = _DEFAULT_SPACED_REPETITION_DAYS
    game_phases: list[int] | None = None
    tactical_patterns: list[int] | None = None
    game_types: list[int] | None = None
    player_colors: list[int] | None = None
    difficulty_ranges: list[tuple[int, int]] | None = None


@dataclass(frozen=True)
class BlunderPuzzle:
    game_id: str
    ply: int
    blunder_uci: str
    blunder_san: str
    fen: str
    source: str
    username: str
    eval_before: int
    eval_after: int
    cp_loss: int
    player_color: str
    best_move_uci: str | None
    best_move_san: str | None
    best_line: str | None
    best_move_eval: int | None
    game_phase: int | None = None
    tactical_pattern: int | None = None
    tactical_reason: str | None = None
    difficulty: int | None = None
    missed_mate_depth: int | None = None
    tactical_squares: list[str] | None = None
    game_url: str | None = None
    pre_move_uci: str | None = None
    pre_move_fen: str | None = None


class Trainer:
    def __init__(
        self,
        games: GameRepository,
        attempts: PuzzleAttemptRepository,
        analysis: AnalysisRepository,
    ):
        self.games = games
        self.attempts = attempts
        self.analysis = analysis

    async def pick_random_blunder(
        self,
        filters: BlunderFilter | None = None,
    ) -> BlunderPuzzle:
        criteria = filters or BlunderFilter()
        candidates = await self._gather_candidates(criteria)
        if not candidates:
            raise ValueError("No blunders found.")

        weights = await self._compute_weights(candidates)
        blunder = random.choices(candidates, weights=weights, k=1)[0]
        return await self._build_puzzle(
            blunder,
            str(blunder["game_id"]),
            int(blunder["ply"]),
        )

    async def get_specific_blunder(self, game_id: str, ply: int) -> BlunderPuzzle:
        blunder = await self.analysis.get_move_analysis(game_id, ply)
        if not blunder:
            raise ValueError(f"No analysis found for game {game_id} ply {ply}")
        return await self._build_puzzle(blunder, game_id, ply)

    async def _gather_candidates(
        self,
        criteria: BlunderFilter,
    ) -> list[dict[str, object]]:
        merged_game_side_map = await self.games.get_all_game_side_map()
        if not merged_game_side_map:
            raise ValueError("No games found.")

        blunders = await self.analysis.fetch_blunders_with_tactics(
            game_phases=criteria.game_phases,
            tactical_patterns=criteria.tactical_patterns,
            player_colors=criteria.player_colors,
            game_types=criteria.game_types,
        )
        candidates = filter_blunders(blunders, merged_game_side_map)
        candidates = _filter_by_difficulty(candidates, criteria.difficulty_ranges)
        candidates = await self._filter_by_date(
            candidates,
            criteria.start_date,
            criteria.end_date,
        )
        return await self._filter_recently_solved(
            candidates,
            criteria.exclude_recently_solved,
            criteria.spaced_repetition_days,
        )

    async def _filter_by_date(
        self,
        candidates: list[dict[str, object]],
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, object]]:
        if not (start_date or end_date) or not candidates:
            return candidates

        kept = []
        for candidate in candidates:
            game = await self.games.get_game(str(candidate["game_id"]))
            if game and _date_in_range(game.get("end_time_utc"), start_date, end_date):
                kept.append(candidate)
        return kept

    async def _filter_recently_solved(
        self,
        candidates: list[dict[str, object]],
        exclude_recently_solved: bool,
        spaced_repetition_days: int,
    ) -> list[dict[str, object]]:
        if not exclude_recently_solved or not candidates:
            return candidates

        recently_solved = await self.attempts.get_recently_solved_puzzles(
            days=spaced_repetition_days,
        )
        if not recently_solved:
            return candidates

        return [
            b
            for b in candidates
            if (b["game_id"], int(b["ply"])) not in recently_solved
        ]

    async def _compute_weights(
        self,
        candidates: list[dict[str, object]],
    ) -> list[float]:
        failure_rates = await self.attempts.get_failure_rates_by_pattern()
        has_history = bool(failure_rates)
        return [_weight_for_blunder(b, failure_rates, has_history) for b in candidates]

    async def _build_puzzle(
        self,
        blunder: dict[str, object],
        game_id: str,
        ply: int,
    ) -> BlunderPuzzle:
        blunder_uci = str(blunder["uci"])
        best_move_uci = blunder.get("best_move_uci")

        game = await self.games.load_game(game_id)
        board = board_before_ply(game, ply)
        pre_move_uci, pre_move_fen = (
            (move_uci_at_ply(game, ply - 1), board_before_ply(game, ply - 1).fen())
            if ply > 1
            else (None, None)
        )
        source, username = _source_and_username(
            await self.games.get_game(game_id),
        )

        return BlunderPuzzle(
            game_id=game_id,
            ply=ply,
            blunder_uci=blunder_uci,
            blunder_san=str(blunder.get("san") or blunder_uci),
            fen=board.fen(),
            source=source,
            username=username,
            eval_before=int(blunder.get("eval_before", 0)),
            eval_after=int(blunder.get("eval_after", 0)),
            cp_loss=int(blunder.get("cp_loss", 0)),
            player_color="white" if int(blunder["player"]) == 0 else "black",
            best_move_uci=best_move_uci,
            best_move_san=blunder.get("best_move_san"),
            best_line=blunder.get("best_line"),
            best_move_eval=blunder.get("best_move_eval"),
            game_phase=blunder.get("game_phase"),
            tactical_pattern=blunder.get("tactical_pattern"),
            tactical_reason=blunder.get("tactical_reason"),
            difficulty=blunder.get("difficulty"),
            missed_mate_depth=blunder.get("missed_mate_depth"),
            tactical_squares=_compute_tactical_squares(
                board,
                blunder_uci,
                best_move_uci,
            ),
            game_url=extract_game_url(game),
            pre_move_uci=pre_move_uci,
            pre_move_fen=pre_move_fen,
        )


def _filter_by_difficulty(
    candidates: list[dict[str, object]],
    difficulty_ranges: list[tuple[int, int]] | None,
) -> list[dict[str, object]]:
    if not difficulty_ranges or not candidates:
        return candidates
    return [
        b
        for b in candidates
        if (d := b.get("difficulty")) is not None
        and any(lo <= d <= hi for lo, hi in difficulty_ranges)
    ]


def _date_in_range(
    game_date: object,
    start_date: str | None,
    end_date: str | None,
) -> bool:
    if not isinstance(game_date, str):
        return False
    if start_date and game_date < start_date:
        return False
    return not (end_date and game_date > end_date)


def _weight_for_blunder(
    blunder: dict[str, object],
    failure_rates: dict[object, float],
    has_history: bool,
) -> float:
    weight = _mate_depth_multiplier(blunder.get("missed_mate_depth"))

    if has_history:
        pattern = blunder.get("tactical_pattern")
        if pattern is not None and pattern not in failure_rates:
            weight *= _WEIGHT_UNSEEN_PATTERN
        else:
            weight *= 1.0 + failure_rates.get(pattern, 0.0)

    difficulty = blunder.get("difficulty")
    if isinstance(difficulty, int):
        if difficulty <= _DIFFICULTY_EASY:
            weight *= _WEIGHT_EASY_DIFFICULTY
        elif difficulty >= _DIFFICULTY_HARD:
            weight *= _WEIGHT_HARD_DIFFICULTY

    return weight


def _mate_depth_multiplier(missed_mate_depth: object) -> float:
    if not isinstance(missed_mate_depth, int) or missed_mate_depth <= 0:
        return 1.0
    if missed_mate_depth <= _MATE_DEPTH_VERY_SHORT:
        return _WEIGHT_MATE_VERY_SHORT
    if missed_mate_depth <= _MATE_DEPTH_SHORT:
        return _WEIGHT_MATE_SHORT
    return 1.0


def _source_and_username(game_metadata: dict[str, object] | None) -> tuple[str, str]:
    if not game_metadata:
        return "any", ""  # noqa: WPS226 — sentinel `any` for "no source filter".
    return (
        str(game_metadata.get("source", "any")),  # noqa: WPS226 — same sentinel.
        str(game_metadata.get("username", "")),
    )


def _compute_tactical_squares(
    board: chess.Board,
    blunder_uci: str,
    best_move_uci: str | None,
) -> list[str] | None:
    if not best_move_uci:
        return None

    blunder_move = _safe_parse_uci(blunder_uci)
    if not blunder_move or blunder_move not in board.legal_moves:
        return None

    try:
        result = classify_blunder_tactics(
            board,
            blunder_move,
            _safe_parse_uci(best_move_uci),
        )
    except (AssertionError, ValueError):
        return None

    seen: list[str] = []
    for tactic in (result.missed_tactic, result.allowed_tactic):
        for sq in getattr(tactic, "squares", None) or ():
            name = chess.square_name(sq)
            if name not in seen:
                seen.append(name)
    return seen or None


def _safe_parse_uci(uci: str) -> chess.Move | None:
    with contextlib.suppress(ValueError):
        return chess.Move.from_uci(uci)
    return None

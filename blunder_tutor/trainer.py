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
from blunder_tutor.utils.pgn_utils import board_before_ply, extract_game_url


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
    tactical_squares: list[str] | None = None
    game_url: str | None = None


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
        username: str | list[str],
        source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        exclude_recently_solved: bool = True,
        spaced_repetition_days: int = 30,
        game_phases: list[int] | None = None,
        tactical_patterns: list[int] | None = None,
        game_types: list[int] | None = None,
        player_colors: list[int] | None = None,
        difficulty_ranges: list[tuple[int, int]] | None = None,
    ) -> BlunderPuzzle:
        usernames = [username] if isinstance(username, str) else username

        merged_game_side_map = {}
        actual_source = source
        actual_username = username if isinstance(username, str) else usernames[0]

        for uname in usernames:
            game_side_map = await self.games.get_username_side_map(uname, source)
            merged_game_side_map.update(game_side_map)

        if not merged_game_side_map:
            raise ValueError("No games found for the requested user/source.")

        blunders = await self.analysis.fetch_blunders_with_tactics(
            game_phases=game_phases,
            tactical_patterns=tactical_patterns,
            player_colors=player_colors,
            game_types=game_types,
        )
        candidates = filter_blunders(blunders, merged_game_side_map)

        if difficulty_ranges and candidates:
            candidates = [
                b
                for b in candidates
                if b.get("difficulty") is not None
                and any(lo <= b["difficulty"] <= hi for lo, hi in difficulty_ranges)
            ]

        if (start_date or end_date) and candidates:
            filtered_candidates = []
            for blunder in candidates:
                game_id = blunder["game_id"]
                game = await self.games.get_game(game_id)
                if not game:
                    continue

                game_date = game.get("end_time_utc")
                if not game_date:
                    continue

                if start_date and game_date < start_date:
                    continue
                if end_date and game_date > end_date:
                    continue

                filtered_candidates.append(blunder)

            candidates = filtered_candidates

        if exclude_recently_solved and candidates:
            recently_solved = await self.attempts.get_recently_solved_puzzles(
                actual_username, days=spaced_repetition_days
            )

            if recently_solved:
                candidates = [
                    b
                    for b in candidates
                    if (b["game_id"], int(b["ply"])) not in recently_solved
                ]

        if not candidates:
            raise ValueError("No blunders found for the requested user/source.")

        weights = await self._compute_weights(candidates, actual_username)
        blunder = random.choices(candidates, weights=weights, k=1)[0]
        game_id = str(blunder["game_id"])
        ply = int(blunder["ply"])
        blunder_uci = str(blunder["uci"])
        blunder_san = str(blunder["san"] or blunder_uci)
        eval_before = int(blunder.get("eval_before", 0))
        eval_after = int(blunder.get("eval_after", 0))
        cp_loss = int(blunder.get("cp_loss", 0))
        player = int(blunder["player"])
        player_color = "white" if player == 0 else "black"

        best_move_uci = blunder.get("best_move_uci")
        best_move_san = blunder.get("best_move_san")
        best_line = blunder.get("best_line")
        best_move_eval = blunder.get("best_move_eval")
        blunder_game_phase = blunder.get("game_phase")
        blunder_tactical_pattern = blunder.get("tactical_pattern")
        blunder_tactical_reason = blunder.get("tactical_reason")
        blunder_difficulty = blunder.get("difficulty")

        game = await self.games.load_game(game_id)
        board = board_before_ply(game, ply)
        game_url = extract_game_url(game)

        game_metadata = await self.games.get_game(game_id)
        if game_metadata:
            actual_source = game_metadata.get("source", "any")
            actual_username = username if isinstance(username, str) else "multi"

        # Compute tactical squares on-the-fly for highlighting
        tactical_squares = self._compute_tactical_squares(
            board, blunder_uci, best_move_uci
        )

        return BlunderPuzzle(
            game_id=game_id,
            ply=ply,
            blunder_uci=blunder_uci,
            blunder_san=blunder_san,
            fen=board.fen(),
            source=actual_source,
            username=actual_username,
            eval_before=eval_before,
            eval_after=eval_after,
            cp_loss=cp_loss,
            player_color=player_color,
            best_move_uci=best_move_uci,
            best_move_san=best_move_san,
            best_line=best_line,
            best_move_eval=best_move_eval,
            game_phase=blunder_game_phase,
            tactical_pattern=blunder_tactical_pattern,
            tactical_reason=blunder_tactical_reason,
            difficulty=blunder_difficulty,
            tactical_squares=tactical_squares,
            game_url=game_url,
        )

    async def _compute_weights(
        self,
        candidates: list[dict[str, object]],
        username: str,
    ) -> list[float]:
        failure_rates = await self.attempts.get_failure_rates_by_pattern(username)
        has_history = bool(failure_rates)

        weights = []
        for blunder in candidates:
            w = 1.0

            # Patterns the player fails at more get higher weight
            pattern = blunder.get("tactical_pattern")
            if has_history:
                rate = failure_rates.get(pattern, 0.0)
                # Unseen patterns get a bonus so they're explored
                if pattern is not None and pattern not in failure_rates:
                    w *= 1.5
                else:
                    w *= 1.0 + rate

            # Higher-difficulty positions are more valuable to practice
            difficulty = blunder.get("difficulty")
            if difficulty is not None:
                if difficulty <= 30:
                    w *= 1.3  # easy = should have seen it
                elif difficulty >= 70:
                    w *= 0.7  # very hard = less learnable

            weights.append(w)

        return weights

    def _compute_tactical_squares(
        self,
        board: chess.Board,
        blunder_uci: str,
        best_move_uci: str | None,
    ) -> list[str] | None:
        """Compute squares involved in the tactical pattern for highlighting."""
        if not best_move_uci:
            return None

        blunder_move = None
        best_move = None

        with contextlib.suppress(ValueError):
            blunder_move = chess.Move.from_uci(blunder_uci)

        with contextlib.suppress(ValueError):
            best_move = chess.Move.from_uci(best_move_uci)

        if not blunder_move:
            return None

        # Verify the moves are legal on this board
        if blunder_move not in board.legal_moves:
            return None

        try:
            result = classify_blunder_tactics(board, blunder_move, best_move)
        except (AssertionError, ValueError):
            # If tactical analysis fails, return None
            return None

        squares = []

        # Get squares from missed tactic (best move)
        if result.missed_tactic and result.missed_tactic.squares:
            for sq in result.missed_tactic.squares:
                squares.append(chess.square_name(sq))

        # Get squares from allowed tactic
        if result.allowed_tactic and result.allowed_tactic.squares:
            for sq in result.allowed_tactic.squares:
                sq_name = chess.square_name(sq)
                if sq_name not in squares:
                    squares.append(sq_name)

        return squares if squares else None

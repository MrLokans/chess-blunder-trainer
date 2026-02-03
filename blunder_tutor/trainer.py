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
from blunder_tutor.utils.pgn_utils import board_before_ply


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
    tactical_squares: list[str] | None = None  # Squares involved in the tactic


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
        )
        candidates = filter_blunders(blunders, merged_game_side_map)

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

        blunder = random.choice(candidates)
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

        game = await self.games.load_game(game_id)
        board = board_before_ply(game, ply)

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
            tactical_squares=tactical_squares,
        )

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

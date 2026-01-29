from __future__ import annotations

import random
from dataclasses import dataclass

from blunder_tutor.analysis.filtering import filter_blunders
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

        blunders = await self.analysis.fetch_blunders()
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

        game = await self.games.load_game(game_id)
        board = board_before_ply(game, ply)

        game_metadata = await self.games.get_game(game_id)
        if game_metadata:
            actual_source = game_metadata.get("source", "any")
            actual_username = username if isinstance(username, str) else "multi"

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
        )

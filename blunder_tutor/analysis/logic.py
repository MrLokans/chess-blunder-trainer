from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import chess
import chess.engine
import chess.pgn
from tqdm import tqdm

from blunder_tutor.constants import MATE_SCORE_ANALYSIS
from blunder_tutor.index import read_index
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.utils.chess_utils import score_to_cp
from blunder_tutor.utils.pgn_utils import load_game


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: int = 50
    mistake: int = 100
    blunder: int = 200


def _is_mate_score(score: chess.engine.PovScore, side: chess.Color) -> bool:
    """Check if the score represents a forced mate."""
    pov = score.pov(side)
    return pov.is_mate()


def _classify(delta: int, thresholds: Thresholds) -> str:
    if delta >= thresholds.blunder:
        return "blunder"
    if delta >= thresholds.mistake:
        return "mistake"
    if delta >= thresholds.inaccuracy:
        return "inaccuracy"
    return "good"


def _class_to_int(label: str) -> int:
    return {"good": 0, "inaccuracy": 1, "mistake": 2, "blunder": 3}[label]


def _iter_moves(game: chess.pgn.Game) -> Iterable[tuple[int, chess.Move, chess.Board]]:
    board = game.board()
    move_number = 1
    for move in game.mainline_moves():
        board_before = board.copy(stack=False)
        yield move_number, move, board_before
        board.push(move)
        if board.turn == chess.WHITE:
            move_number += 1


class GameAnalyzer:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        games_repo: GameRepository,
        engine_path: str,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.games_repo = games_repo
        self.engine_path = engine_path
        self._log = logging.getLogger("GameAnalyzer")

    def analyze_game(
        self,
        game_id: str,
        depth: int | None = 14,
        time_limit: float | None = None,
        thresholds: Thresholds | None = None,
    ) -> None:
        thresholds = thresholds or Thresholds()
        pgn_path = self.games_repo.find_game_path(game_id)
        game = load_game(pgn_path)

        analyzed_at = datetime.now(UTC).isoformat()
        moves: list[dict[str, object]] = []

        limit = (
            chess.engine.Limit(depth=depth)
            if time_limit is None
            else chess.engine.Limit(time=time_limit)
        )

        with chess.engine.SimpleEngine.popen_uci(self.engine_path) as engine:
            for move_number, move, board in _iter_moves(game):
                player = board.turn
                info_before = engine.analyse(board, limit)
                eval_before = score_to_cp(info_before["score"], player)
                san = board.san(move)
                ply = (board.fullmove_number - 1) * 2 + (
                    1 if player == chess.WHITE else 2
                )

                # Extract best move and line from engine analysis
                pv = info_before.get("pv", [])
                best_move_uci = None
                best_move_san = None
                best_line = []
                best_move_eval = None

                if pv:
                    best_move_uci = pv[0].uci()
                    best_move_san = board.san(pv[0])

                    # Build best line in SAN notation (up to 5 moves)
                    temp_board = board.copy()
                    for pv_move in pv[:5]:
                        best_line.append(temp_board.san(pv_move))
                        temp_board.push(pv_move)

                    # Compute evaluation after playing the best move (for caching)
                    best_move_board = board.copy()
                    best_move_board.push(pv[0])
                    info_best = engine.analyse(best_move_board, limit)
                    best_move_eval = score_to_cp(info_best["score"], player)

                board_after = board.copy(stack=False)
                board_after.push(move)

                # Check if move delivers checkmate - this is never a blunder
                if board_after.is_checkmate():
                    eval_after = MATE_SCORE_ANALYSIS  # Winning mate
                    delta = 0
                    cp_loss = 0
                    class_label = "good"
                else:
                    info_after = engine.analyse(board_after, limit)
                    eval_after = score_to_cp(info_after["score"], player)

                    delta = eval_before - eval_after
                    cp_loss = max(0, delta)

                    # If we had a winning mate before and still have a winning position,
                    # don't penalize for "missing" the fastest mate
                    if (
                        _is_mate_score(info_before["score"], player)
                        and eval_after > 500
                    ):
                        # Still winning significantly, not a real blunder
                        cp_loss = min(cp_loss, thresholds.inaccuracy - 1)

                    class_label = _classify(cp_loss, thresholds)

                moves.append(
                    {
                        "ply": ply,
                        "move_number": move_number,
                        "player": "white" if player == chess.WHITE else "black",
                        "uci": move.uci(),
                        "san": san,
                        "eval_before": eval_before,
                        "eval_after": eval_after,
                        "delta": delta,
                        "cp_loss": cp_loss,
                        "classification": _class_to_int(class_label),
                        "best_move_uci": best_move_uci,
                        "best_move_san": best_move_san,
                        "best_line": " ".join(best_line) if best_line else None,
                        "best_move_eval": best_move_eval,
                    }
                )

        self.analysis_repo.write_analysis(
            game_id=game_id,
            pgn_path=str(pgn_path),
            analyzed_at=analyzed_at,
            engine_path=self.engine_path,
            depth=depth,
            time_limit=time_limit,
            thresholds={
                "inaccuracy": thresholds.inaccuracy,
                "mistake": thresholds.mistake,
                "blunder": thresholds.blunder,
            },
            moves=moves,
        )
        return

    def analyze_bulk(
        self,
        data_dir: Path,
        depth: int | None = 14,
        time_limit: float | None = None,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> dict[str, int]:
        processed = 0
        skipped = 0
        analyzed = 0

        records = list(read_index(data_dir, source=source, username=username))
        if limit is not None:
            records = records[:limit]

        self._log.info("Processing games in %s", data_dir)
        with tqdm(total=len(records), desc="Analyze games", unit="game") as progress:
            for record in records:
                game_id = str(record.get("id"))
                if self.analysis_repo.analysis_exists(game_id) and not force:
                    skipped += 1
                    processed += 1
                    progress.update(1)
                    continue
                self.analyze_game(
                    game_id=game_id,
                    depth=depth,
                    time_limit=time_limit,
                )
                analyzed += 1
                processed += 1
                progress.update(1)

        return {"processed": processed, "analyzed": analyzed, "skipped": skipped}

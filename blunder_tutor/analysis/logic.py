from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import chess
import chess.engine
import chess.pgn
from tqdm import tqdm

from blunder_tutor.constants import MATE_SCORE_ANALYSIS
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.utils.chess_utils import score_to_cp


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: int = 50
    mistake: int = 100
    blunder: int = 200


def _is_mate_score(score: chess.engine.PovScore, side: chess.Color) -> bool:
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
        game = self.games_repo.load_game(game_id)

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

                pv = info_before.get("pv", [])
                best_move_uci = None
                best_move_san = None
                best_line = []
                best_move_eval = None

                if pv:
                    best_move_uci = pv[0].uci()
                    best_move_san = board.san(pv[0])

                    temp_board = board.copy()
                    for pv_move in pv[:5]:
                        best_line.append(temp_board.san(pv_move))
                        temp_board.push(pv_move)

                    best_move_board = board.copy()
                    best_move_board.push(pv[0])
                    info_best = engine.analyse(best_move_board, limit)
                    best_move_eval = score_to_cp(info_best["score"], player)

                board_after = board.copy(stack=False)
                board_after.push(move)

                if board_after.is_checkmate():
                    eval_after = MATE_SCORE_ANALYSIS
                    delta = 0
                    cp_loss = 0
                    class_label = "good"
                else:
                    info_after = engine.analyse(board_after, limit)
                    eval_after = score_to_cp(info_after["score"], player)

                    delta = eval_before - eval_after
                    cp_loss = max(0, delta)

                    if (
                        _is_mate_score(info_before["score"], player)
                        and eval_after > 500
                    ):
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
            pgn_path="",
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

        game_ids = self.games_repo.list_unanalyzed_game_ids(source, username)
        if limit is not None:
            game_ids = game_ids[:limit]

        self._log.info("Processing %d games", len(game_ids))
        with tqdm(total=len(game_ids), desc="Analyze games", unit="game") as progress:
            for game_id in game_ids:
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
